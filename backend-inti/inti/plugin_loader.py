"""Plugin Loader — Agent Plugins Spec 1.0.0.

Descubre plugins en la carpeta plugins/, valida manifiestos,
y registra skills en la DB via SkillDefinition.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from inti.config import settings

logger = logging.getLogger("inti.plugin_loader")


class PluginLoader:
    def __init__(self, plugins_dir: str | None = None):
        raw = plugins_dir or settings.plugins_dir
        # Resolver relativo a backend-inti/ (donde corre uvicorn)
        resolved = Path(raw)
        if not resolved.is_absolute():
            resolved = Path(__file__).parent.parent / raw
        self.plugins_dir = resolved.resolve()
        self._discovered: list[dict] = []

    @property
    def discovered(self) -> list[dict]:
        return self._discovered

    def discover(self) -> list[dict]:
        """Escanea plugins/ y devuelve manifiestos validos."""
        self._discovered = []
        if not self.plugins_dir.exists():
            logger.info(f"Plugins dir not found: {self.plugins_dir}. Creating it.")
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return []

        for plugin_path in sorted(self.plugins_dir.iterdir()):
            if not plugin_path.is_dir() or plugin_path.name.startswith("."):
                continue
            manifest_file = plugin_path / "plugin.json"
            if not manifest_file.exists():
                logger.debug(f"Skipping {plugin_path.name}: no plugin.json")
                continue

            try:
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                errors = self._validate_manifest(manifest, plugin_path)
                if errors:
                    logger.warning(f"Invalid manifest in {plugin_path.name}: {errors}")
                    continue

                manifest["_path"] = str(plugin_path)
                self._discovered.append(manifest)
                logger.info(f"Discovered plugin: {manifest['name']} v{manifest['version']}")
            except Exception as e:
                logger.warning(f"Error loading plugin {plugin_path.name}: {e}")

        return self._discovered

    def _validate_manifest(self, manifest: dict, plugin_path: Path) -> list[str]:
        errors = []
        if not manifest.get("name"):
            errors.append("missing 'name'")
        if not manifest.get("version"):
            errors.append("missing 'version'")
        # Validate paths don't escape plugin root (§4.1)
        for skill_path in manifest.get("skills", []):
            resolved = (plugin_path / "skills" / f"{skill_path}.md").resolve()
            if not str(resolved).startswith(str(plugin_path.resolve())):
                errors.append(f"skill path escape: {skill_path}")
        return errors

    async def register_skills(self, manifest: dict) -> int:
        """Registra skills de un plugin en la DB. Devuelve count."""
        from inti.database import async_session
        from inti.models.skill_definition import SkillDefinition
        from sqlalchemy import select

        plugin_name = manifest["name"]
        plugin_path = Path(manifest["_path"])
        count = 0

        for skill_ref in manifest.get("skills", []):
            skill_file = plugin_path / "skills" / f"{skill_ref}.md"
            if not skill_file.exists():
                logger.warning(f"Skill file not found: {skill_file}")
                continue

            try:
                content = skill_file.read_text(encoding="utf-8")
                parsed = self._parse_skill_md(content)
                if not parsed.get("name"):
                    parsed["name"] = skill_ref.split("/")[-1]

                async with async_session() as db:
                    # Check if skill already exists for this plugin
                    result = await db.execute(
                        select(SkillDefinition).where(
                            SkillDefinition.name == parsed["name"]
                        )
                    )
                    existing = result.scalar_one_or_none()

                    tags = parsed.get("tags", [])
                    tags.append(plugin_name)

                    if existing:
                        existing.description = parsed.get("description", existing.description or "")
                        existing.steps_json = json.dumps(parsed.get("steps", []))
                        existing.best_practices_json = json.dumps(parsed.get("best_practices", []))
                        existing.tags_json = json.dumps(tags)
                    else:
                        db.add(SkillDefinition(
                            name=parsed["name"],
                            description=parsed.get("description", f"Skill from {plugin_name}"),
                            steps_json=json.dumps(parsed.get("steps", [])),
                            best_practices_json=json.dumps(parsed.get("best_practices", [])),
                            tags_json=json.dumps(tags),
                        ))
                    await db.commit()
                    count += 1
            except Exception as e:
                logger.warning(f"Error registering skill {skill_ref}: {e}")

        return count

    def _parse_skill_md(self, content: str) -> dict[str, Any]:
        """Parsea SKILL.md al formato SkillDefinition."""
        parsed: dict[str, Any] = {"steps": [], "best_practices": [], "tags": []}

        # Extract title (first # heading)
        title_match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
        if title_match:
            parsed["name"] = title_match.group(1).strip()

        # Extract metadata
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("**Categoria**:"):
                pass  # metadata, not a step
            elif line.startswith("**Tags**:"):
                parsed["tags"] = [t.strip() for t in line.replace("**Tags**:", "").split(",")]

        # Extract description (text between title and Steps)
        desc_parts = []
        in_steps = False
        for line in content.split("\n"):
            if line.strip().startswith("## Steps"):
                in_steps = True
                continue
            if line.strip().startswith("## Best Practices"):
                in_steps = False
                continue
            if not in_steps and not line.startswith("#") and not line.startswith("**") and line.strip():
                desc_parts.append(line.strip())
        if desc_parts:
            parsed["description"] = " ".join(desc_parts[:3])

        # Extract steps
        in_steps = False
        for line in content.split("\n"):
            if line.strip().startswith("## Steps"):
                in_steps = True
                continue
            if line.strip().startswith("## Best Practices"):
                in_steps = False
                continue
            if in_steps and line.strip().startswith(("- ", "1. ", "2. ", "3. ", "4. ", "5. ")):
                step = re.sub(r"^\d+\.\s*|- ", "", line.strip()).strip()
                if step:
                    parsed["steps"].append(step)

        # Extract best practices
        in_bp = False
        for line in content.split("\n"):
            if line.strip().startswith("## Best Practices"):
                in_bp = True
                continue
            if in_bp and line.strip().startswith("- "):
                bp = line.strip()[2:].strip()
                if bp:
                    parsed["best_practices"].append(bp)

        return parsed

    async def register_plugins(self) -> dict:
        """Descubre y registra todos los plugins. Devuelve resumen."""
        from inti.database import async_session
        from inti.models.plugin_definition import PluginDefinition
        from sqlalchemy import select

        manifests = self.discover()
        if not manifests:
            logger.info("No plugins discovered")
            return {"discovered": 0, "registered": 0, "skills": 0}

        registered = 0
        total_skills = 0

        for manifest in manifests:
            async with async_session() as db:
                result = await db.execute(
                    select(PluginDefinition).where(PluginDefinition.name == manifest["name"])
                )
                existing = result.scalar_one_or_none()
                if existing:
                    existing.version = manifest.get("version", existing.version)
                    existing.description = manifest.get("description", existing.description or "")
                    existing.path = manifest["_path"]
                else:
                    db.add(PluginDefinition(
                        name=manifest["name"],
                        version=manifest.get("version", "1.0.0"),
                        description=manifest.get("description", ""),
                        path=manifest["_path"],
                        enabled=True,
                    ))
                await db.commit()
                registered += 1

            skills_count = await self.register_skills(manifest)
            total_skills += skills_count

        logger.info(f"Plugins: {registered} plugins, {total_skills} skills registered")
        return {"discovered": len(manifests), "registered": registered, "skills": total_skills}


plugin_loader = PluginLoader()
