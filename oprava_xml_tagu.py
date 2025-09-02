import os
import re
import xml.etree.ElementTree as ET

def oprav_tagy_ve_slozce(slozka):
    for fname in os.listdir(slozka):
        if fname.endswith(".xml"):
            cesta = os.path.join(slozka, fname)
            with open(cesta, "r", encoding="utf-8") as f:
                obsah = f.read()

            obsah = re.sub(r"<(slide|variant|section|repetition) '([^']+)'>",
                           r'<\1 name="\2">', obsah)

            try:
                root = ET.fromstring(obsah)
            except ET.ParseError as e:
                print(f"Chyba v souboru {fname}: {e}")
                continue

            for variant in root.findall("variant"):
                typ_cislo = {'v': 1, 'r': 1, 'b': 1}
                for section in variant.findall("section"):
                    name = section.attrib.get("name", "")
                    if len(name) == 1 and name in typ_cislo:
                        new_name = f"{name}{typ_cislo[name]}"
                        typ_cislo[name] += 1
                        section.set("name", new_name)

            for repetition in root.findall("repetition"):
                text = repetition.text
                if text:
                    words = re.findall(r'\b[vrb]\b', text)
                    for w in words:
                        text = re.sub(rf'\b{w}\b', f"{w}1", text)
                    repetition.text = text

            novy_obsah = ET.tostring(root, encoding="unicode", method="xml")
            with open(cesta, "w", encoding="utf-8") as f:
                f.write(novy_obsah)

            print(f"Opraveno: {fname}")

slozka_s_pisnemi = "./songs"
oprav_tagy_ve_slozce(slozka_s_pisnemi)
