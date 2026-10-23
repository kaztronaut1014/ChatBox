from __future__ import annotations

import hashlib
from zipfile import ZipFile
from lxml import etree


SOURCE = r"D:\source\ChatBox\tmp\report_work\source.docx"
OUTPUT = r"D:\source\ChatBox\tmp\report_work\Mau_BaoCao_ThayPhuoc_prepared.docx"
EXPECTED_SOURCE_HASH = "8986E37CC42DC20182CB07DE4D1DDD502AB64D7B1AB8249511F4BCCB1541A7B2"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"w": W, "r": R}


def read_docx(path):
    with ZipFile(path) as zf:
        return {name: zf.read(name) for name in zf.namelist()}


source_hash = hashlib.sha256(open(SOURCE, "rb").read()).hexdigest().upper()
assert source_hash == EXPECTED_SOURCE_HASH, source_hash
src, out = read_docx(SOURCE), read_docx(OUTPUT)
source_doc = etree.fromstring(src["word/document.xml"])
output_doc = etree.fromstring(out["word/document.xml"])
source_body = source_doc.find(f"{{{W}}}body")
output_body = output_doc.find(f"{{{W}}}body")


def cover_nodes(body):
    nodes = []
    for child in body:
        if etree.QName(child).localname in {"bookmarkStart", "sdt", "bookmarkEnd"} and len(nodes) < 4:
            nodes.append(child)
        else:
            break
    return nodes


src_cover, out_cover = cover_nodes(source_body), cover_nodes(output_body)
assert len(src_cover) == len(out_cover) == 4
assert [etree.tostring(x, method="c14n") for x in src_cover] == [etree.tostring(x, method="c14n") for x in out_cover]
src_sections = source_doc.xpath("//w:sectPr", namespaces=NS)
out_sections = output_doc.xpath("//w:sectPr", namespaces=NS)
assert len(src_sections) == len(out_sections) == 3
assert [etree.tostring(x, method="c14n") for x in src_sections] == [etree.tostring(x, method="c14n") for x in out_sections]

rels = etree.fromstring(out["word/_rels/document.xml.rels"])
relmap = {r.get("Id"): r.get("Target") for r in rels.findall(f"{{{PKG}}}Relationship")}
embedded = output_doc.xpath("//@r:embed", namespaces=NS)
for rid in embedded:
    target = "word/" + relmap[rid]
    assert target in out, f"Missing image target: {target}"
new_figures = {
    "architecture.png", "message_flow.png", "erd.png", "theory_ecdh.png",
    "theory_hkdf.png", "theory_aesgcm.png", "theory_ecc_roles.png",
    "theory_password_keys.png", "theory_tde.png", "theory_layers.png",
}
linked_figures = {relmap[rid].split("/")[-1] for rid in embedded}
assert new_figures <= linked_figures, new_figures - linked_figures
seq_fields = output_doc.xpath("//w:instrText/text()", namespaces=NS)
figure_captions = sum("SEQ Hinh" in text for text in seq_fields)
table_captions = sum("SEQ Bang" in text for text in seq_fields)
assert figure_captions == 10, figure_captions
assert table_captions == 8, table_captions
text = " ".join(output_doc.xpath("//w:t/text()", namespaces=NS)).casefold()
assert "shop fruit" not in text and "cửa hàng trái cây" not in text
assert "chương 2: cơ sở lý thuyết" in text
assert "tde" in text and "hkdf" in text and "aes-gcm" in text
print("source_sha256", source_hash)
print("prepared_sha256", hashlib.sha256(open(OUTPUT, "rb").read()).hexdigest().upper())
print("cover_controls_preserved", len(out_cover), "section_properties_preserved", len(out_sections))
print("figure_captions", figure_captions, "table_captions", table_captions)
print("embedded_image_relationships", len(embedded), "new_figure_assets", len(new_figures))
print("visible_text_chars", len(text))
print("QA PASS")
