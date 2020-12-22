:: This batch script will start all python scripts in the background
@echo off
for %%f in (*.py) do start /B /MIN /LOW pythonw.exe %%f