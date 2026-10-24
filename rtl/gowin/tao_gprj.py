# rtl/gowin/tao_gprj.py — biến một thư mục dựng của pnr_v3.sh (có build.tcl + src/) thành project Gowin mở được bằng IDE:
# sinh fpga_project.gprj (danh sách file lấy từ các dòng add_file của build.tcl) và impl/fpga_project_process_config.json
# (mẫu process_config_mau.json, sửa TopModule, IncludePath, OUTPUT_BASE_NAME theo build.tcl).
#   python -I rtl/gowin/tao_gprj.py <thư mục dựng>
import json
import pathlib
import re
import sys

KIND = {".v": "file.verilog", ".cst": "file.cst", ".sdc": "file.sdc"}


def main():
    w = pathlib.Path(sys.argv[1]).resolve()
    tcl = (w / "build.tcl").read_text(encoding="utf-8")
    files = re.findall(r"^add_file (\S+)$", tcl, re.M)
    top = re.search(r"-top_module (\S+)", tcl).group(1)
    inc = re.findall(r"-include_path (\S+)", tcl)
    base = (re.search(r"-output_base_name (\S+)", tcl) or [None, "fpga_project"])[1]
    rows = "\n".join(f'        <File path="{f}" type="{KIND[pathlib.Path(f).suffix]}" enable="1"/>' for f in files)
    (w / f"{base}.gprj").write_text(
        '<?xml version="1" encoding="UTF-8"?>\n<!DOCTYPE gowin-fpga-project>\n<Project>\n    <Template>FPGA</Template>\n'
        '    <Version>5</Version>\n    <Device name="GW2A-18C" pn="GW2A-LV18PG256C8/I7">gw2a18c-011</Device>\n'
        f"    <FileList>\n{rows}\n    </FileList>\n</Project>\n", encoding="utf-8", newline="\n")
    cfg = json.loads((pathlib.Path(__file__).parent / "process_config_mau.json").read_text(encoding="utf-8"))
    cfg.update(TopModule=top, IncludePath=[str(w / p).replace("\\", "/") for p in inc], OUTPUT_BASE_NAME=base)
    (w / "impl").mkdir(exist_ok=True)
    (w / "impl" / f"{base}_process_config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8", newline="\n")
    print(f"{w / (base + '.gprj')}: {len(files)} file, top {top}")


if __name__ == "__main__":
    main()
