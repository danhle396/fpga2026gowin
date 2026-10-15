@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo Golden RTL Simulation - FPGA Fall Detection (20 vectors)
echo ============================================================

where iverilog >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Icarus Verilog is not installed or not in PATH.
    echo Install Icarus Verilog first, then reopen this file.
    pause
    exit /b 1
)

where vvp >nul 2>nul
if errorlevel 1 (
    echo [ERROR] vvp is not available in PATH.
    pause
    exit /b 1
)

rem Single source of parameters (RA-01): quant_params.json -> src\cnn_params.vh,
rem tb\vec_in.mem, tb\vec_exp.mem. Needs Python 3 + numpy.
echo [0/2] Generating parameters from quant_params.json...
python -I "..\..\tools\gen_cnn_params.py"
if errorlevel 1 (
    echo [FAIL] gen_cnn_params.py failed. Do not use stale src\cnn_params.vh.
    pause
    exit /b 1
)

for %%f in (src\weights.mem src\bias.mem src\cnn_params.vh tb\vec_in.mem tb\vec_exp.mem tb_cnn_core_golden.v) do (
    if not exist "%%f" (
        echo [ERROR] Missing %%f
        pause
        exit /b 1
    )
)

echo [1/2] Compiling RTL...
rem -g2001 works on Icarus 0.9.7 and newer versions (R8).
iverilog -g2001 -I src -s tb_cnn_core_golden -o golden_sim.vvp ^
  tb_cnn_core_golden.v ^
  src\cnn_core.v ^
  src\cnn_controller.v ^
  src\conv1d_engine.v ^
  src\requantize_relu.v ^
  src\maxpool1d_engine.v ^
  src\feature_ram.v ^
  src\gap_engine.v ^
  src\gap_buffer.v ^
  src\dense_engine.v ^
  src\argmax4.v ^
  src\mac_unit.v ^
  src\weight_rom.v ^
  src\bias_rom.v

if errorlevel 1 (
    echo.
    echo [FAIL] Compile failed.
    pause
    exit /b 1
)

echo.
echo [2/2] Running simulation (2-3 minutes on Icarus 0.9.7)...
echo.
vvp golden_sim.vvp

echo.
echo Expected last lines:
echo   KET QUA: 20/20 vector khop golden, cycles/inference=699800
echo   PASS
echo.
pause
