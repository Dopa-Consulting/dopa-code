"""API de workspace: git status + branch actual."""

import subprocess
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException

router = APIRouter()


@router.get("/browse")
async def browse_folder():
    """Abre un dialogo nativo de Windows para seleccionar carpeta."""
    import subprocess
    result = subprocess.run(
        ["powershell", "-Command",
         "Add-Type -AssemblyName System.Windows.Forms; "
         "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
         "$f.Description = 'Selecciona el workspace de Dopa Code'; "
         "if ($f.ShowDialog() -eq 'OK') { $f.SelectedPath } else { '' }"],
        capture_output=True, text=True, timeout=30,
    )
    path = result.stdout.strip()
    if path:
        return {"path": path}
    return {"path": ""}


@router.get("/changes")
async def workspace_changes(path: str = Query(...), diff: str = Query("0")):
    """Devuelve git status + opcionalmente diff del workspace."""
    ws = Path(path).resolve()
    if not ws.exists() or not ws.is_dir():
        raise HTTPException(status_code=400, detail="Path invalido o no existe")

    try:
        branch_r = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(ws), capture_output=True, text=True, timeout=5,
        )
        branch = branch_r.stdout.strip()

        status_r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(ws), capture_output=True, text=True, timeout=5,
        )
        raw = status_r.stdout

        # Per-file stats: +N -N
        stat_r = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=str(ws), capture_output=True, text=True, timeout=10,
        )
        stat_lines = stat_r.stdout.strip().split("\n")

        files = []
        for line in raw.split("\n"):
            if not line.strip():
                continue
            # BUG-WORK-001: NO usar line.strip() completo — el formato es "XY path"
            # Usar split con maxsplit para obtener status y path correctamente
            parts = line.split(maxsplit=1)
            if len(parts) >= 2:
                status = parts[0]
                fpath = parts[1].strip()
            elif len(line) >= 3:
                # Fallback: formato con espacios
                status = line[:2].strip()
                fpath = line[3:].strip()
            else:
                continue
            # Buscar stats para este archivo
            stats = ""
            for sl in stat_lines:
                if sl.strip().endswith(fpath) or f" {fpath}" in sl or f"{fpath} " in sl:
                    stat_parts = sl.strip().split("|")
                    if len(stat_parts) >= 2:
                        stats = stat_parts[-1].strip()
                    break
            files.append({
                "status": status,
                "path": fpath,
                "stats": stats,
            })

        result = {
            "is_git": True,
            "branch": branch or "unknown",
            "files": files,
            "raw": raw if raw else "(working tree limpio)",
        }

        # Diff completo (opcional, para expandir archivos)
        if diff == "1":
            diff_r = subprocess.run(
                ["git", "diff"],
                cwd=str(ws), capture_output=True, text=True, timeout=15,
            )
            result["diff"] = diff_r.stdout or "(sin diff)"

        return result
    except FileNotFoundError:
        return {"is_git": False, "error": "git no disponible"}
    except subprocess.TimeoutExpired:
        return {"is_git": True, "branch": "unknown", "files": [], "raw": "(timeout)"}
    except Exception as e:
        return {"is_git": False, "error": str(e)[:200]}
