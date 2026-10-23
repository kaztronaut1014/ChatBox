# Working contract: ChatBox course project report

## Reference file and fidelity

- Reference: `D:\Documents\BMTT\Mau_BaoCao_ThayPhuoc.docx`
- SHA-256 before editing: `8986E37CC42DC20182CB07DE4D1DDD502AB64D7B1AB8249511F4BCCB1541A7B2`
- User instruction: rewrite the report in this file, preserve the cover and retain the existing student and instructor information.
- The body starts at “LỜI MỞ ĐẦU”. The first two top-level structured-document controls are the two HUTECH cover pages. Preserve their XML and embedded visual content unchanged.
- The template has A4 pages, portrait; left margin 1.18 in, right 0.79 in, top/bottom 0.79 in; header/footer distance 0.5 in. Body text visually follows Times New Roman, justified, 1.5 line spacing. Chapter headings are centered, uppercase, bold. Subheadings are left aligned and bold.
- The package has 3 `sectPr` nodes: one with the first cover, one at the front-matter/content boundary (Roman page numbering), and the final Arabic-numbered content section (starts at page 1). Preserve the first cover section properties, reuse the front-matter boundary after the new lists, and preserve the final section properties.
- Header parts contain page fields. Preserve headers, footers, page geometry, styles, numbering, cover image relationships, and all package parts not required for new body text/figures.
- The companion sample PDF is 40 pages and demonstrates the HUTECH cover and academic body style. Its pagination is not treated as authoritative for the customized DOCX.

## Rewrite scope and content plan

- Keep both existing cover pages exactly as authored.
- Replace all remaining old content, including stale contents, figure/table lists, chapters, old shop content, screenshots, and references.
- New front matter: Lời mở đầu, Lời cảm ơn, Nhiệm vụ đồ án, Nhận xét của giảng viên, Mục lục, Danh mục hình, Danh mục bảng.
- New five chapters: (1) Tổng quan; (2) Cơ sở lý thuyết; (3) Phân tích và thiết kế hệ thống; (4) Cài đặt, vận hành và kết quả; (5) Kết luận và hướng phát triển; then Tài liệu tham khảo.
- Distinguish design from implementation. Accurately describe source code: Streamlit client, FastAPI service, SQL Server via pyodbc, P-256 ECDH, HKDF-SHA256, AES-256-GCM, local encrypted private-key files using scrypt + AES-GCM, unsalted one-pass SHA-256 password hashes, SQL Server TDE setup script, startup database/schema initialization, and the limitations in the handoff/source.
- Do not claim the repository has automated tests; no `tests` directory exists. Distinguish source-code behavior, user-reported SQL Server/TDE observations, and future test cases.
- Do not include certificate/key backup files, passwords, connection secrets, or placeholder secret values.

## Figures, tables, citations, QA

- Add original diagrams for ECDH, HKDF, AES-GCM, ECC scheme roles, account-password/private-key protection, TDE, security-layer scope, system architecture, message processing, and relational schema; captions and automatic figure-list field use the retained style.
- Include compact tables for API, schema/field lifecycle, algorithm roles, and verification/limitations.
- Use numbered references to primary sources: NIST SP 800-56A Rev. 3, NIST SP 800-38D, RFC 5869, RFC 7914, Microsoft Learn TDE, PyCA Cryptography, OWASP Password Storage, and OWASP SQL Injection Prevention.
- Render the prepared DOCX and inspect every page. Before overwriting the retained reference, verify the two cover controls and their section properties are unchanged. The final target is the exact original path; because it is outside the writable workspace, stage and QA the completed DOCX in the workspace, then request the required write escalation for the final replacement.

## QA results and remaining limitation

- The prepared DOCX retains two cover controls, all 3 source section-property nodes, A4 portrait geometry, margins, headers/footers, styles, and cover image. Section and heading audits report 2 sections and a consistent Heading 1/2/3 hierarchy. The source DOCX still matches the recorded SHA-256 before final replacement.
- The report has 5 chapters, 8 source citations, 8 comparison/schema/API/verification tables, and 10 original diagrams, including 7 new figures in the theoretical chapter. Package QA verifies 10 figure captions, 8 table captions, all image relationships, the original cover controls and section properties, and no visible stale shop content.
- The bundled DOCX renderer was invoked and diagnosed: no bundled `soffice.exe` exists on PATH. A hidden Microsoft Word COM render was attempted; COM activation stalls before document open. Therefore final page count and per-page visual inspection are unavailable in this environment. The two covers are structurally preserved and their XML nodes are checked unchanged; diagrams were visually inspected as PNGs.
- Exact body typography inherits from retained style definitions; existing Heading and Normal styles are retained. The 7 new theory illustrations were rendered as PNGs and visually inspected together for text fit, legibility, and diagram flow.
