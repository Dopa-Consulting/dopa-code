# modern-python
**Categoria**: development
**Tags**: python, tooling, uv, ruff, pytest, trail-of-bits

## Steps
1. Revisar tooling actual: ¿pip o uv? ¿mypy o ruff? ¿black o ruff format?
2. Migrar a uv para gestión de paquetes (más rápido que pip)
3. Configurar ruff para linting + formatting (reemplaza flake8, isort, black)
4. Configurar pytest con coverage (pytest-cov)
5. Agregar type checking (ruff o mypy)
6. Configurar pre-commit hooks para CI local
7. Actualizar CI para usar las nuevas herramientas

## Best Practices
- Un solo tool para cada categoría (ruff para lint+format)
- Configuración en pyproject.toml, no en setup.cfg/tox.ini
- Tests con pytest.mark.asyncio para código async
- Coverage mínimo 80% para código nuevo
- CI debe correr lint + typecheck + tests en cada PR
