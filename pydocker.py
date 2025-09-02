import docker
import tempfile
import os
from typing import List, Dict, Optional


class PyDocker:
    def __init__(self, image: str = "python:3.10-slim", install_cmd: str = ""):
        self.image = image
        self.install_cmd = install_cmd
        self.client = docker.from_env()

    def run_container(self, files: List[Dict[str, str]], timeout: int = 30) -> str:
        """
        Spin up a new container, copy files, execute as needed, and return STDOUT.
        files: List of dicts with keys: filename, file_data, execute (None, 'python', or 'bash')
        """
        import traceback

        # Create a temporary directory to store files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write files to temp directory
            for file in files:
                file_path = os.path.join(tmpdir, file["filename"])
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file["file_data"])

            # Build command: install + execute files
            all_commands = []

            # Add install command if provided
            if self.install_cmd:
                all_commands.append(self.install_cmd)

            # Add file execution commands
            exec_cmds = []
            for file in files:
                if file.get("execute") == "python":
                    exec_cmds.append(f"python {file['filename']}")
                elif file.get("execute") == "bash":
                    exec_cmds.append(f"bash {file['filename']}")

            if exec_cmds:
                # Redirect install output to /dev/null, only capture file execution output
                if self.install_cmd:
                    install_silent = f"({self.install_cmd}) > /dev/null 2>&1"
                    file_exec = " && ".join(exec_cmds)
                    command = f"{install_silent} && {file_exec}"
                else:
                    command = " && ".join(exec_cmds)
            else:
                return ""

            command = f"bash -c '{command}'"
            print(f"[PyDocker] Spinning up container with image: {self.image}")
            print(f"[PyDocker] Command: {command}")
            try:
                container = self.client.containers.run(
                    self.image,
                    command=command,
                    detach=True,
                    tty=True,
                    working_dir="/workspace",
                    volumes={tmpdir: {"bind": "/workspace", "mode": "rw"}},
                )
                print(f"[PyDocker] Container started: {container.short_id}")
                result = container.wait(timeout=timeout)
                logs = container.logs().decode("utf-8")
                return logs
            except Exception as e:
                print(f"[PyDocker] Error running container: {e}")
                traceback.print_exc()
                return f"[PyDocker] Exception: {e}"
            finally:
                try:
                    container.remove(force=True)
                    print(f"[PyDocker] Container removed.")
                except Exception as e:
                    print(f"[PyDocker] Error removing container: {e}")

    def kill_all(self):
        """Kill all containers started from this image."""
        for container in self.client.containers.list(
            all=True, filters={"ancestor": self.image}
        ):
            container.remove(force=True)
