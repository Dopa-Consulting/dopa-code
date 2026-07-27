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
async def workspace_changes(path: str = Query(...)):
    """Devuelve el git status del workspace."""
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

        files = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            if len(line) >= 3:
                files.append({
                    "status": line[:2].strip() or "??",
                    "path": line[3:].strip(),
                })

        return {
            "is_git": True,
            "branch": branch or "unknown",
            "files": files,
            "raw": raw if raw else "(working tree limpio)",
        }
    except FileNotFoundError:
        return {"is_git": False, "error": "git no disponible"}
    except subprocess.TimeoutExpired:
        return {"is_git": True, "branch": "unknown", "files": [], "raw": "(timeout)"}
    except Exception as e:
        return {"is_git": False, "error": str(e)[:200]}
