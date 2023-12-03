import subprocess
import shlex

while True:
    # wait for input
    print("Enter a command:")
    command = input()
    command = "python3 main.py " + command
    args = shlex.split(command)
    try:
        subprocess.Popen(args)

        # Immediately after starting the subprocess, control is returned to the main script
        print(f"Started subprocess: {' '.join(args)}")

    except FileNotFoundError:
        print(f"Command not found: {args[0]}")
    except Exception as e:
        print(f"An error occurred: {e}")
