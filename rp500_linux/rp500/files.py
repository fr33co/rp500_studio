"""Archivos de preset `.rp500p` (XML compatible con gdigi) y respaldo JSON."""
import json
import xml.etree.ElementTree as ET

NS = "http://www.digitech.com/xml/preset"


def _labels(catalog, mods):
    out = {}
    for e in catalog:
        for it in e["items"]:
            for t in it["types"]:
                for p in t["params"]:
                    out.setdefault((p["id"], p["position"]), p["label"])
    for k, m in mods.items():
        out.setdefault(k, m["label"])
    return out


def write_rp500p(path, name, params, catalog, mods):
    names = _labels(catalog, mods)
    root = ET.Element("RP500Preset", {"SchemaVersion": "1.2", "xmlns": NS})
    ET.SubElement(root, "Name").text = name
    ps = ET.SubElement(root, "Params")
    for (pid, pos), val in sorted(params.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        p = ET.SubElement(ps, "Param")
        ET.SubElement(p, "ID").text = str(pid)
        ET.SubElement(p, "Position").text = str(pos)
        ET.SubElement(p, "Value").text = str(val)
        if (pid, pos) in names:
            ET.SubElement(p, "Name").text = names[(pid, pos)]
    ET.indent(root, "  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def read_preset_file(path):
    """-> (nombre, {(id, pos): valor}) desde .rp500p (XML) o .json propio."""
    if path.lower().endswith(".json"):
        with open(path) as f:
            d = json.load(f)
        return d["name"], {(i, p): v for i, p, v in d["params"]}
    root = ET.parse(path).getroot()
    strip = lambda t: t.rsplit("}", 1)[-1]
    if not strip(root.tag).startswith("RP500"):
        raise ValueError(f"no es un preset de RP500 ({strip(root.tag)})")
    name, params = "", {}
    for el in root:
        if strip(el.tag) == "Name":
            name = (el.text or "").strip()
        elif strip(el.tag) == "Params":
            for p in el:
                f = {strip(c.tag): (c.text or "").strip() for c in p}
                params[(int(f["ID"]), int(f["Position"]))] = int(f["Value"])
    return name, params
