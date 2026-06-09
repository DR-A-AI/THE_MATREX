import asyncio
import logging
import sys

logger = logging.getLogger("Sovereign.Factory")

class GuillotineTimeout(Exception):
    pass

class HeadlessFactoryBridge:
    """
    Sovereign Code Factory (Headless).
    Executes background compilation, linting, and Language Server operations safely.
    Implements the 'Guillotine' to instantly kill runaway processes.
    """
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def run_headless_task(self, command: list, timeout_seconds: int = 30) -> dict:
        """
        Runs a headless task (e.g., MSBuild, Python Linter) safely in the background.
        If it hangs, the Guillotine falls and the process is slaughtered.
        """
        logger.info(f"[Factory] Dispatching headless command: {' '.join(command)}")
        
        try:
            # Create the background process without blocking the main event loop
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=self.workspace_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Wait for the process with a strict guillotine timeout
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                # 🔪 THE GUILLOTINE 🔪
                logger.error(f"[Factory] 🔪 GUILLOTINE ENGAGED: Process {' '.join(command)} exceeded {timeout_seconds}s limit! Slaughtering process.")
                process.kill()
                await process.communicate() # ensure zombies are reaped
                raise GuillotineTimeout(f"Task exceeded {timeout_seconds}s timeout and was slaughtered.")

            stdout = stdout_bytes.decode('utf-8', errors='replace').strip()
            stderr = stderr_bytes.decode('utf-8', errors='replace').strip()
            
            success = process.returncode == 0
            if not success:
                logger.warning(f"[Factory] Task failed with exit code {process.returncode}")
                
            return {
                "success": success,
                "exit_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr
            }

        except FileNotFoundError:
            logger.error(f"[Factory] Command executable not found: {command[0]}")
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command not found: {command[0]}"
            }
        except Exception as e:
            logger.error(f"[Factory] Unexpected error: {str(e)}")
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e)
            }

async def test_factory():
    factory = HeadlessFactoryBridge("C:\\")
    # Test a simple fast command
    result = await factory.run_headless_task(["cmd.exe", "/c", "echo Factory Online"], timeout_seconds=5)
    print("Fast task:", result)
    
    # Test the Guillotine with a timeout command (ping localhost 10 times takes ~10 seconds)
    try:
        await factory.run_headless_task(["ping", "127.0.0.1", "-n", "10"], timeout_seconds=3)
    except GuillotineTimeout as e:
        print(f"Guillotine test passed: {e}")

if __name__ == "__main__":
    # Ensure proper event loop policy on Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test_factory())
