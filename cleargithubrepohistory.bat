@echo off
REM ==========================================
REM Reset Git History Script for Windows
REM ==========================================

echo.
echo 🔹 Starting Git history reset...
echo.

REM Ask user for the branch name
set /p branchname="Enter the default branch name (usually main or master): "

REM Step 1: Create a new orphan branch
git checkout --orphan temp_branch
if %errorlevel% neq 0 (
    echo ❌ Failed to create orphan branch
    pause
    exit /b
)

REM Step 2: Add all files
git add .
if %errorlevel% neq 0 (
    echo ❌ Failed to add files
    pause
    exit /b
)

REM Step 3: Commit everything
git commit -m "Initial commit"
if %errorlevel% neq 0 (
    echo ❌ Failed to commit files
    pause
    exit /b
)

REM Step 4: Delete old branch
git branch -D %branchname%
if %errorlevel% neq 0 (
    echo ❌ Failed to delete old branch %branchname%
    pause
    exit /b
)

REM Step 5: Rename new branch
git branch -m %branchname%
if %errorlevel% neq 0 (
    echo ❌ Failed to rename branch to %branchname%
    pause
    exit /b
)

REM Step 6: Force push to remote
git push -f origin %branchname%
if %errorlevel% neq 0 (
    echo ❌ Failed to force push to remote
    pause
    exit /b
)

echo.
echo ✅ Git history has been reset successfully!
pause
