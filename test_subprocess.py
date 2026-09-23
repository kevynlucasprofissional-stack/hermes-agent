import subprocess
result = subprocess.run(['python', '-c', 'import workstation; print("workstation imported"); from agent.operational_resolution import operational_resolution_providers; print("Providers:", operational_resolution_providers())'], capture_output=True, text=True)
print('stdout:', result.stdout)
print('stderr:', result.stderr)