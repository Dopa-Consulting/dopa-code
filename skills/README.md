# Skills de Dopa Code

19 skills precargadas que Inti usa para guiar a los agentes. Adaptadas de:

- [obra/superpowers](https://github.com/obra/superpowers) (261k stars)
- [mattpocock/skills](https://github.com/mattpocock/skills) (187k stars)
- [emilkowalski/skills](https://github.com/emilkowalski/skills) (20k stars)
- [anthropics/skills](https://github.com/anthropics/skills) (164k stars)

## Estructura

```
skills/
├── README.md              # Este archivo
├── general/               # 7 skills de desarrollo general
│   ├── brainstorming.md
│   ├── tdd.md
│   ├── debugging.md
│   ├── planning.md
│   ├── code-review.md
│   ├── git-worktrees.md
│   └── subagent-dev.md
├── design/                # 4 skills de diseño UI/UX
│   ├── frontend-design.md
│   ├── animations.md
│   ├── branding.md
│   └── canvas-design.md
├── dopaweb/               # 6 skills especificas de DopaWeb
│   ├── customize-product.md
│   ├── customize-branding.md
│   ├── add-section.md
│   ├── customize-checkout.md
│   ├── payment-byok.md
│   └── backend-refactor.md
└── meta/                  # 2 skills del sistema
    ├── writing-skills.md
    └── using-skills.md
```

## Como se cargan

Al iniciar Inti, `seed_all_skills()` inserta o actualiza las 19 skills en la tabla `skill_definitions`. Son idempotentes: si ya existen, se actualizan.

```python
# En main.py lifespan:
from inti.skills_seeder import seed_all_skills
await seed_all_skills()
```

Para forzar una recarga manual:
```
POST /api/v1/memory/reseed-skills
```

## Como las usa Inti

1. Al crear un job, Inti busca skills por tags relacionados al project_type
2. Las skills se inyectan en el prompt del agente como contexto
3. El agente sigue los `steps` y respeta las `best_practices`
4. Al completar, el PostMortem evalua si la skill fue util
5. El SkillRefiner ajusta `success_rate` y mejora las best practices

## Tags

| Tag | Skills | Significado |
|-----|--------|-------------|
| `universal` | 9 | Funciona con cualquier proyecto |
| `dopaweb` | 9 | Especifico de DopaWeb |
| `design` | 5 | UI/UX y diseño visual |
| `safe` | 4 | No toca logica de negocio |
| `restricted` | 3 | Requiere guardrails activos |
| `meta` | 2 | Sistema de skills |
