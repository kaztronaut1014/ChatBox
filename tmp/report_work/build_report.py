from __future__ import annotations

import copy
import hashlib
import re
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"D:\source\ChatBox")
WORK = ROOT / "tmp" / "report_work"
SOURCE = WORK / "source.docx"
OUTPUT = WORK / "Mau_BaoCao_ThayPhuoc_prepared.docx"
MEDIA = WORK / "media"
MEDIA.mkdir(parents=True, exist_ok=True)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS = {"w": W, "r": R, "wp": WP, "a": A, "pic": PIC}
EMU = 914400
TWIPS_WIDTH = 9072


PREFACE = [
    ("body", "Các ứng dụng nhắn tin lưu lượng lớn thường phải cân bằng khả năng truy cập nhanh với yêu cầu giữ bí mật nội dung. Khi máy chủ lưu văn bản rõ, người có quyền truy vấn cơ sở dữ liệu, kẻ chiếm quyền máy chủ hoặc người lấy được tệp dữ liệu có thể đọc nội dung. Ngược lại, chỉ mã hóa các tệp cơ sở dữ liệu cũng chưa bảo vệ nội dung khi hệ quản trị đang mở dữ liệu để phục vụ truy vấn."),
    ("body", "Đồ án nghiên cứu và xây dựng ứng dụng ChatBox 1-1 để minh họa hai lớp bảo vệ có mục tiêu khác nhau. Ở lớp ứng dụng, hai client dùng ECDH trên đường cong P-256 để tạo bí mật chung, HKDF-SHA256 để dẫn xuất khóa, rồi AES-256-GCM để mã hóa và xác thực nội dung tin nhắn. Backend chỉ nhận gói ciphertext cùng nonce, salt, AAD và metadata. Ở lớp lưu trữ, Transparent Data Encryption (TDE) của Microsoft SQL Server mã hóa các trang dữ liệu và transaction log khi ghi xuống đĩa."),
    ("body", "Hai lớp này không thay thế nhau. Mã hóa đầu cuối nhằm giữ nội dung tin nhắn khỏi backend và người chỉ đọc được bảng Messages; TDE nhằm giảm rủi ro khi tệp dữ liệu hoặc bản sao lưu bị lấy khỏi máy chủ. TDE không mã hóa riêng từng cột và không ngăn quản trị viên có quyền truy vấn đọc dữ liệu khi SQL Server đang chạy. Đồ án phân tích rõ phạm vi bảo vệ và các giả định thay vì xem một thuật toán là lời giải cho mọi rủi ro."),
    ("body", "Sản phẩm minh họa gồm giao diện Streamlit, API FastAPI, lớp xử lý mật mã phía client và cơ sở dữ liệu Microsoft SQL Server. Hệ thống hỗ trợ tạo tài khoản, đăng nhập, công bố khóa công khai, tạo hội thoại 1-1, lưu tin nhắn mã hóa để người nhận đọc lại khi đăng nhập và quản lý khóa riêng đã mã hóa cục bộ. SQL Server được khởi tạo schema bởi backend; TDE được cấu hình riêng bằng tập lệnh quản trị chạy trong SSMS."),
    ("body", "Báo cáo mô tả cả phần đã hiện diện trong mã nguồn lẫn phần còn thiếu. Cụ thể, mật khẩu tài khoản hiện được băm một lượt bằng SHA-256 không salt theo phạm vi đồ án; cách này không chống tốt việc đoán mật khẩu ngoại tuyến nếu bảng hash bị lộ. Khóa riêng người dùng được bảo vệ theo một luồng riêng bằng scrypt và AES-GCM trong tệp cục bộ. Khóa ECDH dài hạn chưa cung cấp forward secrecy, và khóa công khai do server phân phối chưa được xác thực bằng fingerprint, chứng chỉ hay chữ ký số."),
    ("body", "Mục tiêu cuối cùng là làm rõ cách dữ liệu đi qua từng lớp, trường nào cần lưu trong SQL, thông tin nào phải giữ ở client, và trạng thái nào cần loại bỏ sau xử lý. Báo cáo cũng ghi nhận giới hạn của bản demo để làm cơ sở nâng cấp, đặc biệt với xác thực khóa, quản lý phiên, bảo vệ mật khẩu, sao lưu khóa riêng và kiểm thử bảo mật."),
]

THANKS = [
    "Em xin chân thành cảm ơn Ban Giám hiệu Trường Đại học Công nghệ TP. Hồ Chí Minh, Khoa Công nghệ Thông tin cùng quý Thầy/Cô đã tạo điều kiện học tập và cung cấp kiến thức để em thực hiện đồ án môn học Bảo mật thông tin.",
    "Em xin bày tỏ lòng biết ơn đến ThS. Nguyễn Trọng Minh Hồng Phước đã hướng dẫn, góp ý và định hướng quá trình lựa chọn phạm vi cũng như hoàn thiện nội dung đồ án. Em cũng cảm ơn gia đình và bạn bè đã động viên trong thời gian thực hiện.",
    "Do thời gian và kinh nghiệm thực tế còn hạn chế, ứng dụng vẫn còn những điểm cần cải thiện. Em mong nhận được góp ý của Thầy và quý Thầy/Cô để có thể hoàn thiện kiến thức chuyên môn và nâng cao chất lượng hệ thống.",
    "Em xin chân thành cảm ơn!",
]

TASKS = [
    "Nghiên cứu vai trò của ECC/ECDH trong thỏa thuận khóa và phân biệt ECDH với ECDSA, ECIES.",
    "Xây dựng luồng mã hóa nội dung tin nhắn phía client bằng ECDH P-256, HKDF-SHA256 và AES-256-GCM; lưu ciphertext và metadata cần thiết trong SQL Server.",
    "Xây dựng backend Python cho tài khoản, khóa công khai, hội thoại 1-1, lưu và truy xuất lịch sử tin nhắn.",
    "Tích hợp Microsoft SQL Server, tạo schema có khóa ngoại và truy vấn tham số; cấu hình TDE bằng script quản trị độc lập với tài khoản ứng dụng.",
    "Phân tích vòng đời dữ liệu và khóa, mô tả giới hạn bảo mật, thiết kế cách kiểm tra tính toàn vẹn, khả năng giải mã và trạng thái mã hóa TDE.",
]

CHAPTERS = [
    ("CHƯƠNG 1: TỔNG QUAN", [
        ("h2", "1.1 Bối cảnh đề tài"),
        ("body", "Tin nhắn là dữ liệu nhạy cảm vì thường chứa thông tin cá nhân, trao đổi công việc và tài liệu riêng. Một ứng dụng client-server thông thường nhận nội dung từ client, xử lý tại backend rồi ghi vào SQL. TLS bảo vệ kênh truyền khi được cấu hình đúng, nhưng không tự làm cho bản ghi trong database trở thành ciphertext; backend và tài khoản truy vấn vẫn có thể nhìn thấy nội dung mà ứng dụng đã giải mã."),
        ("body", "Đồ án chọn ứng dụng chat 1-1 làm tình huống minh họa vì có thể trình bày cụ thể quan hệ giữa hai danh tính, trao đổi khóa, mã hóa từng thông điệp và lưu trữ lịch sử. Mục tiêu không phải xây dựng nền tảng nhắn tin thương mại hoàn chỉnh mà là kiểm tra cách kết hợp mã hóa ở client với cơ chế mã hóa dữ liệu lưu trữ của SQL Server."),
        ("h2", "1.2 Vấn đề cần giải quyết"),
        ("body", "Nếu chỉ dựa vào quyền truy cập SQL, dữ liệu rõ có thể bị đọc khi quyền quản trị bị lạm dụng hoặc khi bản dump được sao chép. Nếu chỉ bật TDE, SQL Server tự giải mã dữ liệu khi vận hành nên người có quyền truy vấn vẫn có thể đọc nội dung. Nếu chỉ mã hóa từng tin ở client nhưng không bảo vệ file database, ciphertext và metadata vẫn có thể bị phân tích hoặc bản sao lưu có thể bị khai thác cho các mục tiêu khác."),
        ("body", "Bài toán vì vậy được chia làm hai câu hỏi: (1) làm sao để backend và SQL không cần biết nội dung tin nhắn; (2) làm sao để file dữ liệu SQL Server được mã hóa khi lưu trên ổ đĩa. Ngoài ra, hệ thống cần lưu đủ nonce, salt, AAD, phiên bản khóa và định danh hội thoại để client có thể xác minh và giải mã về sau."),
        ("h2", "1.3 Mục tiêu"),
        ("h3", "1.3.1 Mục tiêu tổng quát"),
        ("body", "Thiết kế và hiện thực một bản demo ChatBox 1-1 nhằm minh họa bảo vệ nội dung tin nhắn ở cấp ứng dụng, đồng thời sử dụng TDE của Microsoft SQL Server để mã hóa dữ liệu ở trạng thái lưu trữ."),
        ("h3", "1.3.2 Mục tiêu cụ thể"),
        ("bullet", "Tách client, backend API, lớp mật mã và database thành các mô-đun riêng."),
        ("bullet", "Tạo cặp khóa ECC P-256 ở client; dùng ECDH, HKDF-SHA256 và AES-256-GCM để mã hóa tin nhắn."),
        ("bullet", "Không đưa private key, shared secret, khóa AES hay plaintext vào SQL; chỉ lưu ciphertext và metadata cần thiết."),
        ("bullet", "Dùng UUID làm định danh hội thoại; lưu quan hệ thành viên để kiểm tra quyền truy cập lịch sử."),
        ("bullet", "Cấu hình TDE bằng certificate và database encryption key; phân biệt thao tác quản trị TDE với khởi tạo schema của ứng dụng."),
        ("bullet", "Đánh giá giới hạn: password hash SHA-256 một lượt không salt, xác thực khóa công khai, forward secrecy, phiên đăng nhập và khôi phục private key."),
        ("h2", "1.4 Đối tượng và phạm vi"),
        ("body", "Đối tượng nghiên cứu là các thuật toán và cơ chế liên quan đến trao đổi khóa ECC, dẫn xuất khóa, mã hóa xác thực, bảo vệ mật khẩu, SQL Server TDE và lưu trữ dữ liệu chat. Ứng dụng hiện hỗ trợ hội thoại hai người. Mã nguồn dùng Streamlit cho giao diện, FastAPI cho API, thư viện cryptography cho primitive mật mã, pyodbc và ODBC Driver 17 để kết nối SQL Server."),
        ("body", "Đồ án chưa triển khai chat nhóm, đồng bộ nhiều thiết bị, forward secrecy, thu hồi khóa có lưu trữ lịch sử, xác thực public key qua CA/fingerprint, TLS production, rate limit đăng nhập, session store bền vững hoặc quy trình khôi phục lịch sử khi mất private key. ECDSA và ECIES được phân tích để phân biệt vai trò nhưng không phải luồng mã hóa tin nhắn đang chạy."),
        ("h2", "1.5 Phương pháp thực hiện"),
        ("body", "Quy trình gồm khảo sát yêu cầu và mã nguồn hiện tại; chọn primitive chuẩn từ thư viện; mô hình hóa luồng đăng ký, gửi, lưu và nhận tin; thiết kế schema SQL; triển khai các mô-đun client/backend/database; sau đó đối chiếu cấu hình SQL Server và các giới hạn an toàn. Mã nguồn hiện có được dùng làm căn cứ để mô tả chức năng. Những ca chưa có test tự động được ghi là yêu cầu kiểm thử tiếp theo, không gán kết quả đạt khi chưa có bằng chứng."),
        ("h2", "1.6 Bố cục báo cáo"),
        ("body", "Chương 1 trình bày bối cảnh, mục tiêu và phạm vi. Chương 2 giải thích các thuật toán và cơ chế bảo mật. Chương 3 mô tả yêu cầu, kiến trúc, workflow, schema và vòng đời trường dữ liệu. Chương 4 trình bày triển khai, vận hành, kết quả được ghi nhận và các kiểm tra còn thiếu. Chương 5 tổng kết, nêu giới hạn và hướng phát triển."),
    ]),
    ("CHƯƠNG 2: CƠ SỞ LÝ THUYẾT", [
        ("h2", "2.1 Mô hình đe dọa và mục tiêu bảo vệ"),
        ("body", "Mô hình xem xét ba tài sản: nội dung tin nhắn; khóa riêng và khóa dẫn xuất ở client; dữ liệu và khóa mã hóa database trên máy chủ SQL. Các đối tượng có thể gây rủi ro gồm người nghe lén mạng, người chỉ đọc database hoặc file backup bị đánh cắp, người chiếm quyền backend, và người có quyền quản trị SQL. Mức bảo vệ phụ thuộc vào quyền của từng đối tượng và trạng thái hệ thống."),
        ("body", "Mã hóa đầu cuối nhằm bảo vệ bí mật nội dung trước backend và truy vấn SQL thông thường, với giả định khóa riêng của hai client không bị lộ và public key đối phương được xác thực. TDE bảo vệ file database, log và backup khi lưu trữ, nhưng không che nội dung trước SQL Server sau khi engine giải mã trang dữ liệu. Không lớp nào tự chống được malware trên endpoint, chụp màn hình, lộ mật khẩu, tấn công từ chối dịch vụ hoặc sai sót phân quyền."),
        ("h2", "2.2 Mật mã đường cong elliptic và ECDH"),
        ("body", "Trong ECC, khóa công khai là một điểm trên đường cong elliptic; khóa riêng là một số bí mật. Hai bên có thể trao đổi khóa công khai rồi tính cùng một giá trị bí mật bằng phép nhân vô hướng trên đường cong. Với P-256 (SECP256R1), client A dùng private key của mình và public key của B; client B làm tương tự. Kết quả ECDH hai phía giống nhau khi cặp khóa và điểm công khai hợp lệ [1]."),
        ("body", "Trong mã nguồn, `generate_keypair()` tạo khóa riêng P-256 bằng thư viện cryptography, xuất public key dạng DER SubjectPublicKeyInfo và `create_shared_secret()` thực hiện `private_key.exchange(ec.ECDH(), peer_public_key)`. Giá trị trả về là key material thô, chưa phải khóa AES phù hợp; vì vậy bước HKDF là bắt buộc trong workflow."),
        ("body", "ECDH tự nó không chứng minh public key thuộc về username mà server khai báo. Kẻ trung gian có thể thay khóa công khai nếu client tin hoàn toàn vào directory của server. Cần xác thực khóa qua fingerprint so sánh ngoài băng, chứng chỉ/chữ ký được tin cậy hoặc giao thức xác thực khóa. Bản demo hiện kiểm tra định dạng và đường cong khi tải một số khóa, nhưng không có cơ chế xác minh danh tính cryptographic toàn diện."),
        ("figure", "theory_ecdh.png"),
        ("h2", "2.3 HKDF-SHA256"),
        ("body", "HKDF là hàm dẫn xuất khóa theo hai bước Extract và Expand. Extract dùng salt cùng input keying material để tạo pseudorandom key; Expand dùng pseudorandom key, thông tin ngữ cảnh `info` và độ dài đầu ra để sinh khóa theo mục đích. Salt của HKDF không cần bí mật; giá trị này giúp các lần dẫn xuất tách biệt hơn. `info` ràng buộc khóa với ứng dụng và ngữ cảnh, tránh dùng nhầm khóa giữa các mục đích [2]."),
        ("body", "Project gọi `HKDF(algorithm=SHA256, length=32, salt=salt, info=...)`; thông tin ngữ cảnh gồm chuỗi phiên bản ứng dụng và conversation_id. Đầu ra 32 byte tương ứng khóa AES-256. Mỗi tin nhắn tạo salt ngẫu nhiên 16 byte. Salt được lưu cùng message để người nhận có thể tái tạo cùng khóa từ ECDH secret. Salt không phải khóa bí mật và không thay thế nonce của AES-GCM."),
        ("figure", "theory_hkdf.png"),
        ("h2", "2.4 AES-256-GCM và AAD"),
        ("body", "AES là mã hóa đối xứng: cùng một khóa bí mật được dùng để mã hóa và giải mã. GCM kết hợp mã hóa với mã xác thực; nó trả về ciphertext kèm authentication tag. Khi giải mã, nếu ciphertext, tag, nonce, khóa hoặc AAD không khớp, xác thực thất bại và plaintext không được chấp nhận. NIST mô tả GCM như authenticated encryption with associated data [3]."),
        ("body", "Project sử dụng `AESGCM` của thư viện cryptography. Mã hóa sinh nonce 12 byte bằng bộ sinh ngẫu nhiên của hệ điều hành. Ciphertext do API trả về đã gắn tag ở cuối, nên schema lưu chung trong cột `Ciphertext`; không cần tách cột `AuthTag`. Nonce phải duy nhất dưới cùng một khóa; tái sử dụng nonce với khóa GCM là lỗi nghiêm trọng [4]."),
        ("body", "AAD là dữ liệu không mã hóa nhưng được đưa vào phép xác thực. Ở client, AAD chứa conversation_id, username người gửi, username người nhận và phiên bản giao thức. Server có thể đọc AAD nhưng không sửa mà vẫn vượt qua kiểm tra tag. Mã nguồn lưu AAD vào cột riêng để client gửi lại chính xác khi giải mã."),
        ("body", "AES-GCM không cho phép database tìm kiếm theo nội dung plaintext. Nếu cần tìm kiếm, chỉ mục tìm kiếm mã hóa sẽ làm lộ thông tin theo thiết kế và phải phân tích rò rỉ riêng. Với phạm vi hiện tại, SQL tìm theo conversation_id và MessageId, không truy vấn theo từ khóa trong tin."),
        ("figure", "theory_aesgcm.png"),
        ("h2", "2.5 ECDSA và ECIES"),
        ("body", "ECDSA dùng private key để ký và public key để xác minh chữ ký; nó không mã hóa hay giải mã thông điệp. ECIES là một sơ đồ mã hóa kết hợp, thường dùng cơ chế khóa công khai và KDF để thiết lập/bọc khóa đối xứng, sau đó dùng mã hóa đối xứng cho dữ liệu. Đồ án không tự ghép primitive để tạo ECIES. Luồng thực thi tin nhắn hiện tại là ECDH + HKDF + AES-GCM; ECDSA không được gọi trong code của ChatBox."),
        ("figure", "theory_ecc_roles.png"),
        ("h2", "2.6 Băm mật khẩu tài khoản"),
        ("body", "Mã nguồn lưu password tài khoản dưới dạng `SHA256(password UTF-8)` thành chuỗi hex 64 ký tự và so sánh bằng `hmac.compare_digest`. Theo yêu cầu phạm vi của chủ đồ án, phép băm tài khoản không có salt và chỉ thực hiện một lượt. Đây là băm nhanh tổng quát, không phải password hashing chuyên dụng. Nếu hash database bị lộ, kẻ tấn công có thể thử đoán ngoại tuyến với tốc độ cao; rate limit đăng nhập trực tuyến không làm chậm kiểu đoán này."),
        ("body", "OWASP khuyến nghị dùng thuật toán lưu mật khẩu chậm, có cấu hình chi phí và salt duy nhất như Argon2id, scrypt hoặc PBKDF2 thay vì SHA-256 đơn lượt [6]. Trong báo cáo, SHA-256 được ghi là lựa chọn hiện tại của bản demo cùng với rủi ro đó, không được mô tả như một giải pháp password storage an toàn cho sản phẩm thực tế. TDE cũng không khắc phục điểm yếu này nếu attacker lấy được hash từ database đang mở hoặc dump đã giải mã."),
        ("h2", "2.7 Bảo vệ private key cục bộ"),
        ("body", "Khóa riêng ECDH không được lưu vào SQL. Client tuần tự hóa khóa riêng ở định dạng DER PKCS#8, sinh salt 16 byte, dùng scrypt với N=2^15, r=8, p=1 để dẫn xuất khóa 32 byte từ password, rồi mã hóa file bằng AES-GCM với nonce 12 byte. Username đã chuẩn hóa được gắn vào AAD. File chứa magic/version, salt, nonce và ciphertext; các metadata này không bí mật nhưng cần được bảo toàn [8]."),
        ("body", "Salt trong file khóa là salt của scrypt dùng để dẫn xuất khóa mã hóa private key; nó không phải salt trong `PasswordHash` của tài khoản. Đây là hai quy trình khác nhau. Khi đăng nhập, client mở file khóa bằng password, lấy public key tương ứng từ server và so sánh. Mất file khóa hoặc quên password của file khiến client không thể phục hồi private key từ server; tạo khóa mới không khôi phục được lịch sử mã hóa bằng khóa cũ."),
        ("figure", "theory_password_keys.png"),
        ("h2", "2.8 SQL Server, kiểu nhị phân và truy vấn tham số"),
        ("body", "SQL Server dùng `VARBINARY(MAX)` cho ciphertext, public key, AAD và salt khi độ dài có thể thay đổi; `BINARY(12)` lưu nonce AES-GCM có kích thước cố định. Các byte được lưu nguyên dạng nhị phân, không phải văn bản UTF-8. Base64 chỉ là định dạng vận chuyển qua JSON API; backend giải Base64 trước khi insert vào SQL."),
        ("body", "Các truy vấn repository dùng dấu `?` của pyodbc để truyền giá trị tham số thay vì nối username hoặc message vào chuỗi SQL. Truy vấn tham số tách code khỏi dữ liệu và là biện pháp chính giảm SQL injection [7]. Tên database được kiểm tra allowlist trước khi đưa vào câu lệnh tạo database."),
        ("h2", "2.9 Transparent Data Encryption"),
        ("body", "TDE mã hóa trang dữ liệu trước khi ghi xuống file dữ liệu và giải mã khi đọc trang vào bộ nhớ. SQL Server dùng Database Encryption Key (DEK) đối xứng; DEK được bảo vệ bởi certificate lưu trong `master` (hoặc cơ chế EKM). Chuỗi tin cậy trên SQL Server thường gồm Service Master Key, Database Master Key, certificate và DEK. Bản backup của database đang bật TDE cũng được mã hóa bằng DEK [5]."),
        ("body", "Bật TDE trên SQL Server cần tạo master key, certificate, sao lưu certificate và private key, tạo DEK cho database, rồi bật `ALTER DATABASE ... SET ENCRYPTION ON`. Certificate và private key backup phải được giữ riêng khỏi file database; mất certificate có thể làm mất khả năng attach/restore database đã mã hóa. Việc tạo khóa TDE cần quyền quản trị và không nên đặt trong luồng startup của tài khoản ứng dụng."),
        ("body", "TDE mã hóa data-at-rest, không mã hóa riêng từng dòng/cột và không ngăn SQL Server hay người có quyền truy vấn đọc dữ liệu sau khi engine mở database. TDE không thay TLS cho kết nối mạng, không thay mã hóa đầu cuối và không tự giới hạn quyền. Trạng thái `sys.databases.is_encrypted` cho biết database bật TDE; `sys.dm_database_encryption_keys.encryption_state = 3` biểu thị quá trình mã hóa hoàn tất."),
        ("figure", "theory_tde.png"),
        ("h2", "2.10 Phân biệt hai lớp bảo vệ"),
        ("table", [
            ["Thuộc tính", "Mã hóa đầu cuối tại client", "SQL Server TDE"],
            ["Mục tiêu", "Giữ nội dung tin khỏi backend và SQL query", "Bảo vệ file DB/log/backup khi lưu"],
            ["Nơi thực hiện", "Client gửi và nhận", "SQL Server khi ghi/đọc page"],
            ["Dữ liệu SQL nhìn thấy", "Ciphertext tin nhắn và metadata", "Trang dữ liệu đã mã hóa trên đĩa; query runtime vẫn thấy giá trị"],
            ["Khóa", "Private key ở client; session key dẫn xuất tạm thời", "DEK được certificate bảo vệ trong SQL Server"],
            ["Không giải quyết", "Lộ endpoint, xác thực key sai, mất private key", "SQL admin đọc runtime, plaintext gửi từ app, lộ certificate"],
        ]),
        ("figure", "theory_layers.png"),
    ]),
    ("CHƯƠNG 3: PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG", [
        ("h2", "3.1 Yêu cầu hệ thống"),
        ("h3", "3.1.1 Yêu cầu chức năng"),
        ("bullet", "Đăng ký username với password và public key ECC; từ chối username trùng."),
        ("bullet", "Đăng nhập, cấp bearer token cho phiên trong bộ nhớ và đăng xuất."),
        ("bullet", "Tra cứu username/public key, tạo hoặc mở hội thoại 1-1, liệt kê các hội thoại đã lưu."),
        ("bullet", "Mã hóa tin ở client trước khi gửi; server lưu và trả gói tin cho thành viên hội thoại."),
        ("bullet", "Cho phép người nhận tải lại lịch sử sau khi đăng nhập, kể cả khi người nhận offline lúc gửi."),
        ("h3", "3.1.2 Yêu cầu bảo mật"),
        ("bullet", "Không gửi private key, shared secret hoặc khóa AES phiên tới backend."),
        ("bullet", "Không ghi plaintext hoặc password rõ vào SQL hay log."),
        ("bullet", "Dùng AES-GCM để phát hiện thay đổi ciphertext, nonce, AAD hoặc tag."),
        ("bullet", "Kiểm tra thành viên conversation trước thao tác gửi/đọc; dùng truy vấn tham số."),
        ("bullet", "TDE là bước cấu hình riêng bằng quyền quản trị SQL Server; ứng dụng chỉ kiểm tra trạng thái và ghi cảnh báo."),
        ("h2", "3.2 Kiến trúc tổng thể"),
        ("body", "Client Streamlit xử lý giao diện, giữ private key trong session, nạp khóa riêng mã hóa từ thiết bị, lấy public key đối phương, chạy ECDH/HKDF/AES-GCM và gọi API bằng HTTP JSON. FastAPI xác thực bearer token, kiểm tra quyền thành viên, chuyển Base64 thành bytes, gọi repository và không giải mã message. SQL Server giữ tài khoản, public key, hội thoại, thành viên và ciphertext. TDE bảo vệ file SQL tại tầng ổ đĩa."),
        ("figure", "architecture.png"),
        ("caption", "Kiến trúc hai lớp bảo vệ của ChatBox"),
        ("h2", "3.3 Các thành phần và trách nhiệm"),
        ("table", [
            ["Thành phần", "Nhiệm vụ", "Dữ liệu nhạy cảm được giữ"],
            ["Streamlit client", "Đăng ký/đăng nhập, quản lý hội thoại, mã hóa và giải mã tin", "Private key; shared secret và khóa AES khi xử lý; plaintext trong bộ nhớ"],
            ["cipher/ecc", "Tạo P-256, nạp public key DER, thỏa thuận ECDH", "Private key và shared secret"],
            ["cipher/encryption", "HKDF-SHA256, AES-GCM, nonce và xác thực AAD", "Khóa AES tạm thời và plaintext tạm thời"],
            ["FastAPI", "Auth, public-key directory, kiểm tra thành viên, lưu/trả message", "Password được nhận trong request; server không nhận private/session key"],
            ["Repository + pyodbc", "Truy vấn tham số và ánh xạ record SQL", "PasswordHash, public key, ciphertext, metadata"],
            ["SQL Server", "Lưu schema, dữ liệu hội thoại, áp dụng TDE", "Hash tài khoản, public key, ciphertext và metadata"],
        ]),
        ("h2", "3.4 Workflow đăng ký, đăng nhập và khóa"),
        ("body", "Khi đăng ký, client tạo cặp khóa ECC ở thiết bị. Client gửi username, password và public key Base64 đến `/auth/register`. Repository băm password bằng SHA-256 một lượt, insert username, hash và public key. Sau khi đăng ký thành công, client mã hóa private key vào file cục bộ bằng scrypt và AES-GCM. Password không được lưu lại; server không nhận private key."),
        ("body", "Khi đăng nhập, client mở file private key cục bộ bằng password người dùng nhập, gọi `/auth/login`, rồi lấy public key của chính tài khoản để đối chiếu với public key suy ra từ private key vừa mở. Khi khớp, client giữ token và private key trong Streamlit session. Token hiện được giữ trong dictionary tiến trình backend, không có expiration/store bền vững và sẽ mất khi server khởi động lại."),
        ("body", "Nếu file khóa không có trên thiết bị mới, backend không thể gửi lại private key vì khóa đó không được lưu trên server. Khôi phục cần bản sao lưu file khóa. Nếu mất hoàn toàn khóa, tạo cặp khóa mới chỉ thay public key của tài khoản; lịch sử cũ dựa trên private key đã mất không thể giải mã. Cột KeyVersion tăng khi public key được thay, nhưng schema hiện không lưu đầy đủ lịch sử public key theo từng tin."),
        ("h2", "3.5 Workflow xử lý message"),
        ("body", "Khi mở chat, client lấy public key hiện tại của đối phương. Với mỗi message, client sinh salt HKDF 16 byte, dựng AAD theo conversation_id, người gửi, người nhận và phiên bản giao thức, tạo shared secret ECDH, dẫn xuất khóa AES 32 byte rồi gọi AES-GCM với nonce mới. JSON gửi lên API chứa ciphertext, nonce, salt, AAD và key_version dưới dạng Base64."),
        ("figure", "message_flow.png"),
        ("caption", "Các bước mã hóa, lưu và giải mã một tin nhắn"),
        ("body", "Backend chuẩn hóa conversation_id thành UUID, giải mã Base64, kiểm tra nonce dài 12 byte và xác nhận cả người gửi lẫn người nhận là thành viên của cùng hội thoại. Nếu hợp lệ, backend insert bản ghi; không phụ thuộc người nhận có đang online. Khi client nhận lịch sử, client tái tạo khóa bằng private key cục bộ và public key đối phương hiện tại, gửi đúng salt, nonce, ciphertext và AAD vào AES-GCM. Nếu tag không hợp lệ, message bị từ chối giải mã."),
        ("body", "Trong UI hiện tại, danh sách hội thoại được tải khi giao diện chạy lại; khi đang mở chat, Streamlit fragment lấy tin mới theo `after_id` mỗi vài giây. Tin cũ được cache trong session. Điều này giảm việc tải lại toàn bộ message nhưng vẫn là polling theo khoảng thời gian, chưa phải push/WebSocket."),
        ("h2", "3.6 Thiết kế cơ sở dữ liệu"),
        ("figure", "erd.png"),
        ("caption", "Mô hình quan hệ của cơ sở dữ liệu ChatBox"),
        ("table", [
            ["Bảng", "Cột chính", "Kiểu và vai trò"],
            ["dbo.Users", "Username (PK), PasswordHash, PublicKey, KeyVersion, CreatedAt", "Username NVARCHAR(50); hash CHAR(64); public key VARBINARY(MAX); phiên bản INT; thời điểm UTC DATETIME2"],
            ["dbo.Conversations", "ConversationId (PK), CreatedAt", "UNIQUEIDENTIFIER do SQL sinh bằng NEWID(); dùng định danh hội thoại, không ghép username"],
            ["dbo.ConversationMembers", "ConversationId + Username (PK), JoinedAt", "Ánh xạ thành viên; FK đến Conversations và Users; khóa chính kép chống trùng thành viên"],
            ["dbo.Messages", "MessageId (PK), ConversationId, SenderUsername, RecipientUsername, Ciphertext, Nonce, HkdfSalt, Aad, KeyVersion, ProtocolVersion, CreatedAt", "ID BIGINT; ciphertext VARBINARY(MAX); nonce BINARY(12); salt VARBINARY(16); AAD VARBINARY(MAX); thời điểm UTC"],
        ]),
        ("body", "Index trên `(ConversationId, MessageId)` phục vụ tải lịch sử theo hội thoại và thứ tự tăng dần. Repository dùng `MessageId > after_id` để lấy bản ghi mới. Schema giữ sender/recipient là username và liên kết chúng bằng foreign key tới Users. Backend kiểm tra membership trước khi truy vấn hoặc thêm message."),
        ("h2", "3.7 Vòng đời dữ liệu và trường nào được lưu"),
        ("table", [
            ["Giá trị", "Sinh/đọc ở đâu", "Có lưu ở SQL?", "Sau xử lý"],
            ["Password tài khoản", "Nhận tạm ở client/API khi đăng ký hoặc login", "Không; chỉ lưu SHA-256 hex không salt", "Giải phóng khỏi luồng request/session sau xác thực; không log"],
            ["Password đầu vào để mở file khóa", "Client", "Không", "Dùng để dẫn xuất khóa file; không ghi vào file/log"],
            ["Salt scrypt và nonce file khóa", "Client khi lưu private key", "Không", "Lưu trong file khóa mã hóa vì cần để mở file"],
            ["Private key ECDH", "Client", "Không", "Giữ trong session/file khóa đã mã hóa; mất file không phục hồi được"],
            ["Public key ECC", "Client tạo, server phân phối", "Có, VARBINARY(MAX)", "Thông tin công khai; cần quy trình xác thực và xoay khóa"],
            ["ECDH shared secret", "Client mỗi lần dẫn xuất", "Không", "Chỉ tồn tại trong bộ nhớ trong quá trình tính HKDF"],
            ["Khóa AES phiên/tin nhắn", "HKDF trên client", "Không", "Chỉ giữ khi mã hóa/giải mã; không gửi đến API"],
            ["Plaintext", "UI/client trước mã hóa và sau giải mã", "Không", "Hiển thị trong UI; không ghi vào server/database/log"],
            ["Ciphertext + nonce + HKDF salt + AAD", "Client gửi API", "Có, trong Messages", "Cần giữ để xác thực và giải mã lịch sử"],
            ["Conversation/key/protocol version", "Backend/client", "Có", "Metadata hỗ trợ phân quyền và tương thích; không thay thế lưu public key lịch sử"],
            ["TDE DEK/certificate/private-key backup", "Quản trị SQL Server", "Trong hệ phân cấp khóa SQL, không trong bảng ứng dụng", "Backup certificate/private key và bảo vệ tách biệt; không commit secret"],
        ]),
        ("body", "Các trạng thái tạm thời như shared secret, khóa AES và plaintext trung gian cần được loại khỏi luồng xử lý khi không còn dùng, nhưng Python không bảo đảm xóa an toàn từng byte khỏi bộ nhớ do cơ chế quản lý đối tượng. Vì vậy, báo cáo nói “không lưu bền vững/không log”, không khẳng định có thể zeroize triệt để RAM trong bản demo."),
        ("h2", "3.8 Thiết kế TDE và kết nối SQL Server"),
        ("body", "`database/db.py` kết nối tới SQL Server bằng ODBC Driver 17, mặc định Windows Authentication; có thể chọn SQL Authentication qua biến cấu hình. Khi khởi động, backend kết nối `master`, tạo database nếu chưa có, tạo bảng/index còn thiếu và kiểm tra `sys.databases.is_encrypted`. Phần này không tự tạo master key/certificate/DEK TDE. Nếu TDE chưa bật, ứng dụng ghi cảnh báo; quản trị viên chạy `sql/tde_setup.sql` thủ công bằng SSMS."),
        ("body", "Script TDE tạo hoặc dùng master key, certificate, sao lưu certificate và private key ra đường dẫn trên máy SQL Server, tạo DEK AES-256 trong ChatBox, bật encryption và truy vấn `sys.dm_database_encryption_keys` để xem trạng thái. Tài khoản dịch vụ SQL Server cần quyền ghi thư mục backup. Mật khẩu cho master key và private-key backup cần thay bằng giá trị riêng, không commit vào Git, và file backup phải được bảo vệ/tách khỏi bản sao database."),
        ("h2", "3.9 Mô hình quyền và ranh giới tin cậy"),
        ("body", "Client là ranh giới tin cậy của nội dung: nếu client bị malware hoặc private key bị lấy, người tấn công có thể đọc dữ liệu giải mã trên thiết bị. Backend được tin cậy để xác thực tài khoản, phân quyền và duy trì dữ liệu, nhưng thiết kế E2EE không cấp cho backend khóa giải mã message. SQL Server được tin cậy để vận hành TDE; người có quyền đủ cao trên instance vẫn có thể truy vấn dữ liệu runtime. Certificate TDE là bí mật quản trị hạ tầng, khác với ECC key của người dùng."),
        ("body", "Mã nguồn có các truy vấn tham số và kiểm tra membership, nhưng không có rate limit đăng nhập, không đặt thời hạn bearer token, không lưu session ngoài RAM và cấu hình connection hiện bật `TrustServerCertificate=yes` cho môi trường demo. Khi triển khai ra mạng, cần TLS cho client/API và cấu hình xác thực certificate SQL Server; không nên coi thiết lập phát triển cục bộ là cấu hình production."),
    ]),
    ("CHƯƠNG 4: CÀI ĐẶT, VẬN HÀNH VÀ KẾT QUẢ", [
        ("h2", "4.1 Môi trường và thư viện"),
        ("body", "Project được viết bằng Python. `requirements.txt` khai báo cryptography, FastAPI, Uvicorn, Requests, Streamlit và pyodbc. Cơ sở dữ liệu là Microsoft SQL Server; kết nối Python cần ODBC Driver 17 for SQL Server phù hợp với kiến trúc Python 64-bit. SSMS được dùng để chạy script TDE và theo dõi trạng thái encryption. VS Code là môi trường soạn thảo, không phải dịch vụ database."),
        ("h2", "4.2 Cấu trúc project"),
        ("table", [
            ["Thư mục/tệp", "Vai trò"],
            ["client/ui/app.py", "Giao diện Streamlit, auth, danh sách hội thoại, mã hóa/giải mã và lưu private key cục bộ"],
            ["client/main.py", "Mã demo cũ mô phỏng hai client; không phải luồng đăng nhập API hiện dùng"],
            ["server/api.py", "FastAPI endpoints cho đăng ký, đăng nhập, user/public key, hội thoại và message"],
            ["server/main.py", "Chạy Uvicorn cho API trên localhost:8000"],
            ["cipher/ecc/key_agreement.py", "Tạo khóa ECC P-256, nạp public key DER và thực hiện ECDH"],
            ["cipher/ecc/key_storage.py", "Lưu/đọc private key cục bộ đã mã hóa bằng scrypt + AES-GCM"],
            ["cipher/encryption.py", "HKDF-SHA256, AES-GCM, nonce và hàm giải mã xác thực"],
            ["database/db.py", "ODBC connection, khởi tạo database/schema và kiểm tra cờ TDE"],
            ["database/models.py", "Dataclass biểu diễn message và public key"],
            ["database/repositories.py", "Truy vấn tham số cho người dùng, public key, hội thoại và message"],
            ["sql/schema.sql", "DDL tạo database và các bảng/index"],
            ["sql/tde_setup.sql", "Script quản trị cấu hình TDE độc lập với ứng dụng"],
        ]),
        ("body", "Repository hiện không có thư mục `tests`; vì vậy chưa có bộ kiểm thử tự động được version control cùng project. `schema.sql` và `initialize_database()` cùng mô tả schema ban đầu; khi thay đổi cấu trúc cần cập nhật đồng bộ hai nơi để tránh lệch schema."),
        ("h2", "4.3 Các luồng API chính"),
        ("table", [
            ["HTTP", "Endpoint", "Tác dụng"],
            ["POST", "/auth/register", "Tạo user, lưu hash password và public key"],
            ["POST", "/auth/login", "Kiểm tra password hash, cấp bearer token trong bộ nhớ"],
            ["POST", "/auth/logout", "Xóa token khỏi dictionary tiến trình"],
            ["GET", "/users, /users/{username}/public-key", "Liệt kê user và lấy khóa công khai"],
            ["PUT", "/users/me/public-key", "Thay public key và tăng KeyVersion sau khi đăng nhập"],
            ["GET/POST", "/conversations", "Liệt kê hội thoại hoặc tạo/mở hội thoại 1-1"],
            ["POST", "/messages", "Kiểm tra membership và lưu gói ciphertext"],
            ["GET", "/conversations/{id}/messages?after_id=n", "Trả lịch sử theo conversation và cursor MessageId"],
        ]),
        ("h2", "4.4 Khởi tạo SQL Server và TDE"),
        ("body", "Khi server chạy, `initialize_database()` tạo database ChatBox từ `master` nếu chưa tồn tại rồi tạo các bảng, khóa ngoại và index. Vì database được tạo trong server đang kết nối, nó sẽ xuất hiện trong Object Explorer sau khi refresh danh sách Databases trong SSMS. Kết nối thành công và database được tạo đã được người thực hiện xác nhận trong quá trình phát triển."),
        ("body", "TDE không được tự cấu hình bởi endpoint ứng dụng. Script `tde_setup.sql` chạy trong SSMS với quyền quản trị. Trong quá trình vận hành, người thực hiện đã ghi nhận `encryption_state = 3` cho ChatBox, tương ứng trạng thái đã mã hóa hoàn tất. `database/db.py` chỉ đọc cờ `is_encrypted` để log thông tin; nó không xác minh certificate backup, không tạo DEK và không tự đổi mật khẩu certificate."),
        ("h2", "4.5 Kết quả triển khai theo chức năng"),
        ("table", [
            ["Nội dung", "Bằng chứng trong project/vận hành", "Đánh giá đúng phạm vi"],
            ["Tạo tài khoản và đăng nhập", "Endpoint `/auth/register`, `/auth/login`; UI sinh/kiểm tra khóa local", "Đã triển khai trong mã nguồn; không có test tự động đi kèm"],
            ["Khóa riêng ở client", "key_storage dùng scrypt + AES-GCM; so public key khi login", "File khóa được mã hóa cục bộ; không hỗ trợ server recovery"],
            ["Mã hóa message", "UI gọi ECDH, HKDF và AES-GCM; API lưu ciphertext và metadata", "Luồng có trong code; cần test round-trip/tamper riêng để xác nhận đầy đủ"],
            ["Lịch sử/offline", "Messages được insert vào SQL; danh sách conversation và endpoint tải lịch sử", "Backend không yêu cầu recipient online để lưu; recipient cần đúng private key để đọc"],
            ["SQL Server", "Người thực hiện đã kết nối được và tạo database ChatBox", "Đã ghi nhận trên môi trường phát triển"],
            ["TDE", "Trạng thái `encryption_state = 3` được người thực hiện quan sát trong SSMS", "Đã mã hóa hoàn tất trên instance được báo cáo; certificate backup phải tiếp tục được bảo vệ"],
            ["Chống sửa message", "AESGCM.decrypt dùng ciphertext, nonce, AAD và khóa", "Primitive từ chối tag không hợp lệ; project chưa có ca test tự động ghi nhận"],
        ]),
        ("body", "Kết quả trên mô tả mức triển khai và bằng chứng hiện có, không đồng nghĩa với kiểm toán bảo mật hay xác nhận toàn bộ hệ thống chống được tấn công. Để đóng vòng xác minh, cần thêm test tích hợp và lưu kết quả đầu ra, đặc biệt là truy vấn trực tiếp bảng Messages để xác nhận không có plaintext, round-trip Unicode, sửa ciphertext/tag/AAD, khóa sai, user không thuộc conversation và khôi phục file khóa."),
        ("h2", "4.6 Các trường hợp kiểm thử cần hoàn thiện"),
        ("table", [
            ["Ca kiểm tra", "Thao tác", "Kết quả mong đợi", "Trạng thái hiện tại"],
            ["E2E round-trip", "A gửi tin Unicode; B tải và giải mã", "Chuỗi nhận bằng chuỗi gửi", "Chưa có test tự động trong repo"],
            ["Phát hiện sửa đổi", "Thay một byte ciphertext, nonce, AAD hoặc tag", "AES-GCM từ chối giải mã", "Hành vi primitive có trong thư viện; chưa có ca test app"],
            ["Khóa không đúng", "Đăng nhập bằng file khóa thuộc tài khoản khác", "Client phát hiện public key không khớp và không vào chat", "Có nhánh kiểm tra trong UI; cần kiểm thử hồi quy"],
            ["Quyền hội thoại", "User ngoài conversation gọi GET/POST message", "API trả 403", "Có kiểm tra membership trong API; chưa có test tự động"],
            ["Recipient offline", "A gửi khi B không chạy client; B đăng nhập sau", "B tải được bản ghi đã lưu nếu giữ private key", "Backend lưu bền; cần test hai phiên thực tế"],
            ["SQL content", "Đọc trực tiếp `dbo.Messages` bằng SSMS", "Ciphertext nhị phân, nonce, salt, AAD; không thấy plaintext", "Phù hợp schema/code; cần lưu ảnh/chứng cứ kiểm tra"],
            ["TDE", "Đọc DMV `sys.dm_database_encryption_keys`", "`encryption_state = 3` khi scan xong", "Người thực hiện đã báo cáo trạng thái 3"],
        ]),
        ("h2", "4.7 Phân tích giới hạn bảo mật hiện tại"),
        ("bullet", "Password hash SHA-256 đơn lượt, không salt, dễ bị đoán ngoại tuyến; rate limit không được triển khai và dù có cũng chỉ giúp với thử đăng nhập trực tuyến."),
        ("bullet", "Public key lấy từ server chưa được xác thực độc lập; ECDH có thể chịu MITM nếu directory hoặc kết nối bị kiểm soát."),
        ("bullet", "Dùng khóa ECDH dài hạn thay vì khóa ephemeral/protocol ratchet nên chưa có forward secrecy; lộ khóa dài hạn có thể ảnh hưởng lịch sử tương ứng."),
        ("bullet", "Đổi public key làm lịch sử cũ có thể không giải mã được; `KeyVersion` chưa đi kèm lịch sử khóa công khai cần thiết cho từng message."),
        ("bullet", "Bearer token ở RAM không có hạn sử dụng và mất khi server restart; cấu hình HTTP local và `TrustServerCertificate=yes` chỉ phù hợp demo."),
        ("bullet", "TDE chỉ bảo vệ khi dữ liệu lưu trữ; không thay phân quyền, audit, sao lưu tách biệt, bảo vệ certificate, TLS hoặc mã hóa cấp client."),
        ("bullet", "Không có thư mục test tự động; các tuyên bố về integrity, phân quyền và offline delivery cần được chứng minh bằng ca kiểm thử có lưu kết quả."),
    ]),
    ("CHƯƠNG 5: KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN", [
        ("h2", "5.1 Kết luận"),
        ("body", "Đồ án đã xây dựng được mô hình ChatBox 1-1 để minh họa việc tách bảo vệ nội dung khỏi bảo vệ file database. Luồng mã hóa nằm ở client: ECDH P-256 tạo shared secret, HKDF-SHA256 dẫn xuất khóa 32 byte gắn với salt và conversation context, AES-256-GCM mã hóa message và xác thực AAD. Backend lưu ciphertext cùng metadata, kiểm tra thành viên conversation và phục vụ lịch sử; SQL Server lưu public key, hash tài khoản, quan hệ hội thoại và gói mã hóa."),
        ("body", "SQL Server được cấu hình TDE riêng bằng certificate và DEK AES-256. Theo trạng thái được người thực hiện ghi nhận, database đạt `encryption_state = 3`. Kết quả này thể hiện scan mã hóa đã hoàn tất trên môi trường đó; để khôi phục database ở instance khác vẫn cần certificate/private-key backup và mật khẩu tương ứng."),
        ("body", "Kết quả quan trọng về thiết kế là phân biệt đúng loại khóa và phạm vi: ECDH thỏa thuận khóa; HKDF dẫn xuất khóa; AES-GCM mã hóa/xác thực; ECDSA không dùng để mã hóa; TDE bảo vệ data-at-rest. Các trường nonce, HKDF salt và AAD được lưu để giải mã/xác thực, trong khi private key, shared secret và khóa AES không đưa vào SQL."),
        ("h2", "5.2 Hạn chế"),
        ("body", "Bản hiện tại dùng SHA-256 một lượt không salt cho mật khẩu tài khoản theo phạm vi đã chọn, vì vậy không nên xem đây là mô hình lưu mật khẩu đủ an toàn. Public key chưa có cơ chế xác thực đáng tin cậy; protocol chưa có forward secrecy; khóa dài hạn và thay khóa chưa hỗ trợ giải mã an toàn lịch sử cũ. Token lưu trong RAM, thiếu rate limit, thiếu tự động test, chưa có multi-device, và cấu hình kết nối chưa phù hợp production."),
        ("body", "TDE certificate backup hiện phụ thuộc thao tác quản trị và lưu trữ bên ngoài database. Nếu certificate hoặc private key backup mất, backup database mã hóa có thể không phục hồi được. SQL Server TDE cũng không ngăn người có quyền truy vấn nội dung sau khi engine mở database và không giúp tìm kiếm plaintext trong ciphertext."),
        ("h2", "5.3 Hướng phát triển"),
        ("bullet", "Thay password hashing bằng Argon2id hoặc scrypt có salt riêng và tham số chi phí được lưu cùng hash; bổ sung giới hạn thử đăng nhập, thời hạn token và session store bền vững."),
        ("bullet", "Thiết kế xác thực public key bằng fingerprint, chứng chỉ hoặc giao thức có ký; bổ sung cảnh báo khi khóa đối phương thay đổi."),
        ("bullet", "Dùng giao thức chat đã được phân tích như Signal protocol hoặc một protocol ratchet chuẩn để có forward secrecy và khôi phục bảo mật khi khóa bị lộ; không tự thiết kế lại primitive."),
        ("bullet", "Định nghĩa key version theo từng message, lưu gói khóa/metadata cần thiết để lịch sử có thể giải mã qua nhiều lần xoay khóa; xây dựng backup private key mã hóa an toàn cho người dùng."),
        ("bullet", "Bổ sung test tự động cho ECDH/HKDF/AES-GCM, Unicode, tamper, membership, đăng ký/đăng nhập, offline delivery, schema và thao tác xoay khóa."),
        ("bullet", "Bật HTTPS/TLS cho API và kiểm chứng certificate SQL Server; dùng tài khoản SQL ít quyền nhất; bật audit và quản lý secret từ kho an toàn."),
        ("bullet", "Tự động hóa xác minh TDE sau scan, sao lưu certificate/private key theo chính sách, kiểm tra khả năng restore định kỳ và lưu tách biệt với backup database."),
        ("bullet", "Đánh giá chỉ mục tìm kiếm nếu cần; chấp nhận và định lượng rò rỉ metadata thay vì giả định ciphertext có thể tìm kiếm như văn bản rõ."),
        ("body", "Các hướng này cần được ưu tiên theo yêu cầu của đồ án và tài nguyên triển khai. Việc thay thuật toán password hash, protocol chat hoặc cơ chế phục hồi khóa sẽ làm thay đổi mô hình tin cậy, nên phải cập nhật cả thiết kế, code, schema, kiểm thử và cơ sở lý thuyết."),
    ]),
]

REFERENCES = [
    "National Institute of Standards and Technology (NIST), Recommendation for Pair-Wise Key-Establishment Schemes Using Discrete Logarithm Cryptography, Special Publication 800-56A Revision 3, 2018. https://csrc.nist.gov/pubs/sp/800/56/a/r3/final",
    "H. Krawczyk, P. Eronen, HMAC-based Extract-and-Expand Key Derivation Function (HKDF), RFC 5869, IETF, 2010. https://www.rfc-editor.org/rfc/rfc5869",
    "National Institute of Standards and Technology (NIST), Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM) and GMAC, Special Publication 800-38D, 2007. https://csrc.nist.gov/pubs/sp/800/38/d/final",
    "Python Cryptographic Authority, Cryptography Documentation: Elliptic Curve Cryptography, https://cryptography.io/en/stable/hazmat/primitives/asymmetric/ec/; Authenticated Encryption, https://cryptography.io/en/stable/hazmat/primitives/aead/ (truy cập 23/10/2026).",
    "Microsoft Learn, Transparent Data Encryption (TDE) - SQL Server, https://learn.microsoft.com/en-us/sql/relational-databases/security/encryption/transparent-data-encryption?view=sql-server-ver17 (truy cập 23/10/2026).",
    "OWASP Foundation, Password Storage Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html (truy cập 23/10/2026).",
    "OWASP Foundation, SQL Injection Prevention Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html (truy cập 23/10/2026).",
    "C. Percival, S. Josefsson, The scrypt Password-Based Key Derivation Function, RFC 7914, IETF, 2016. https://www.rfc-editor.org/rfc/rfc7914",
]


def font(path: str, size: int):
    return ImageFont.truetype(path, size)


FONT_PATH = r"C:\Windows\Fonts\arial.ttf"
BOLD_PATH = r"C:\Windows\Fonts\arialbd.ttf"


def wrap(draw, text, fnt, width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = word if not current else current + " " + word
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_card(draw, xy, title, lines, fill, outline, title_font, body_font, pad=24):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=22, fill=fill, outline=outline, width=4)
    y = y1 + pad
    draw.text((x1 + pad, y), title, fill="#163B5C", font=title_font)
    y += title_font.size + 12
    for item in lines:
        for line in wrap(draw, item, body_font, x2 - x1 - 2 * pad):
            draw.text((x1 + pad, y), line, fill="#263746", font=body_font)
            y += body_font.size + 8
        y += 5


def arrow(draw, start, end, color="#155E8A", width=7):
    draw.line([start, end], fill=color, width=width)
    import math
    a = math.atan2(end[1] - start[1], end[0] - start[0])
    length, spread = 22, 0.58
    p1 = (end[0] - length * math.cos(a - spread), end[1] - length * math.sin(a - spread))
    p2 = (end[0] - length * math.cos(a + spread), end[1] - length * math.sin(a + spread))
    draw.polygon([end, p1, p2], fill=color)


def diagram_architecture(path: Path):
    im = Image.new("RGB", (1800, 760), "white")
    d = ImageDraw.Draw(im)
    title_font, body_font = font(BOLD_PATH, 31), font(FONT_PATH, 23)
    draw_card(d, (55, 170, 470, 580), "Client A", ["Private key ở thiết bị", "ECDH P-256 + HKDF", "AES-GCM mã hóa trước khi gửi"], "#EAF4FA", "#2675A5", title_font, body_font)
    draw_card(d, (690, 170, 1110, 580), "FastAPI backend", ["Xác thực và kiểm tra quyền", "Nhận ciphertext + metadata", "Không có khóa để giải mã"], "#F1F5F8", "#66839A", title_font, body_font)
    draw_card(d, (1330, 170, 1745, 580), "SQL Server", ["Users / PublicKeys", "Conversations / Members", "Messages + TDE at rest"], "#EDF5EF", "#4F8862", title_font, body_font)
    arrow(d, (470, 310), (685, 310)); arrow(d, (1110, 310), (1325, 310))
    d.text((485, 270), "ciphertext", font=font(BOLD_PATH, 20), fill="#155E8A")
    d.text((1125, 270), "INSERT / SELECT", font=font(BOLD_PATH, 20), fill="#155E8A")
    arrow(d, (1325, 450), (1110, 450), color="#648094")
    arrow(d, (685, 450), (470, 450), color="#648094")
    d.text((1145, 466), "ciphertext", font=font(FONT_PATH, 19), fill="#526A7B")
    d.text((490, 466), "client giải mã", font=font(FONT_PATH, 19), fill="#526A7B")
    d.text((430, 45), "Mã hóa nội dung ở client và mã hóa file SQL ở trạng thái lưu trữ", font=font(BOLD_PATH, 34), fill="#123B5B")
    d.text((120, 650), "Layer 1: E2EE giữ plaintext và khóa ở client", font=font(FONT_PATH, 25), fill="#163B5C")
    d.text((1040, 650), "Layer 2: TDE bảo vệ file database / log", font=font(FONT_PATH, 25), fill="#163B5C")
    im.save(path)


def diagram_flow(path: Path):
    im = Image.new("RGB", (1800, 850), "white")
    d = ImageDraw.Draw(im)
    tfont, bfont = font(BOLD_PATH, 27), font(FONT_PATH, 21)
    d.text((570, 45), "Vòng đời một tin nhắn", font=font(BOLD_PATH, 36), fill="#123B5B")
    cards = [
        ("1  Chuẩn bị khóa", ["Lấy public key đã đăng ký", "ECDH(private local, public peer)" ]),
        ("2  Dẫn xuất", ["Sinh HKDF salt 16 byte", "HKDF-SHA256 -> khóa 32 byte"]),
        ("3  Mã hóa", ["Tạo nonce 12 byte", "AES-GCM(plaintext, AAD)"])
    ]
    xs = [(70, 560), (655, 1145), (1240, 1730)]
    for (title, lines), (x1,x2) in zip(cards,xs):
        draw_card(d,(x1,150,x2,360),title,lines,"#EAF4FA","#2675A5",tfont,bfont,pad=22)
    arrow(d,(560,255),(645,255)); arrow(d,(1145,255),(1230,255))
    draw_card(d,(290,520,830,750),"4  Gửi và lưu",["API kiểm tra thành viên hội thoại","SQL lưu ciphertext, nonce, salt, AAD"],"#F1F5F8","#66839A",tfont,bfont)
    draw_card(d,(970,520,1510,750),"5  Nhận và xác minh",["Tải bản ghi khi online","Dẫn xuất lại khóa; GCM verify rồi giải mã"],"#EDF5EF","#4F8862",tfont,bfont)
    arrow(d,(1325,365),(815,510)); arrow(d,(850,635),(960,635),color="#648094")
    d.text((1000,695),"Tag sai: từ chối plaintext",font=font(BOLD_PATH,20),fill="#A03C3C")
    im.save(path)


def diagram_erd(path: Path):
    im = Image.new("RGB", (1800, 900), "white")
    d = ImageDraw.Draw(im)
    title_font, body_font = font(BOLD_PATH, 28), font(FONT_PATH, 21)
    d.text((690, 35), "ERD - SQL Server", font=font(BOLD_PATH, 36), fill="#123B5B")
    boxes = {
        "Users": (70, 185, 520, 500, ["PK Username", "PasswordHash", "PublicKey", "KeyVersion", "CreatedAt"]),
        "Conversations": (675, 160, 1125, 365, ["PK ConversationId", "CreatedAt"]),
        "ConversationMembers": (675, 550, 1125, 820, ["PK/FK ConversationId", "PK/FK Username", "JoinedAt"]),
        "Messages": (1290, 330, 1740, 775, ["PK MessageId", "FK ConversationId", "FK SenderUsername", "FK RecipientUsername", "Ciphertext", "Nonce / HkdfSalt / Aad", "KeyVersion / ProtocolVersion", "CreatedAt"]),
    }
    for name,(x1,y1,x2,y2,lines) in boxes.items():
        d.rounded_rectangle((x1,y1,x2,y2),radius=18,fill="#F6FAFC",outline="#2675A5",width=4)
        d.rectangle((x1,y1,x2,y1+55),fill="#DDECF5",outline="#2675A5",width=2)
        d.text((x1+18,y1+10),name,font=title_font,fill="#163B5C")
        y=y1+75
        for item in lines:
            d.text((x1+22,y),item,font=body_font,fill="#263746"); y+=45
    # The database has direct foreign keys from Users and Conversations to Messages.
    # ConversationMembers maps the two entities; message membership is checked by API.
    arrow(d,(520,390),(660,650),color="#526A7B",width=5)
    arrow(d,(900,365),(900,540),color="#526A7B",width=5)
    arrow(d,(1125,300),(1280,450),color="#526A7B",width=5)
    d.text((535,490),"1 : N",font=font(BOLD_PATH,20),fill="#526A7B")
    d.text((915,425),"1 : N",font=font(BOLD_PATH,20),fill="#526A7B")
    d.text((1130,365),"1 : N",font=font(BOLD_PATH,20),fill="#526A7B")
    d.text((100,845),"SenderUsername và RecipientUsername là hai FK từ Users đến Messages; API kiểm tra membership trước khi đọc/ghi.",font=font(FONT_PATH,19),fill="#526A7B")
    im.save(path)


def centered_text(draw, center_x, y, text, fnt, fill):
    box = draw.textbbox((0, 0), text, font=fnt)
    draw.text((center_x - (box[2] - box[0]) / 2, y), text, font=fnt, fill=fill)


def diagram_theory_ecdh(path: Path):
    im = Image.new("RGB", (1800, 720), "white")
    d = ImageDraw.Draw(im)
    title_font, body_font = font(BOLD_PATH, 34), font(FONT_PATH, 29)
    centered_text(d, 900, 35, "Hai phía tính được cùng bí mật bằng ECDH P-256", font(BOLD_PATH, 40), "#123B5B")
    draw_card(d, (55, 160, 575, 440), "Client Alice", ["Private key: dA", "Public key: QA = dA × G", "Tính: ZA = dA × QB"], "#EAF4FA", "#2675A5", title_font, body_font, pad=25)
    draw_card(d, (1225, 160, 1745, 440), "Client Bob", ["Private key: dB", "Public key: QB = dB × G", "Tính: ZB = dB × QA"], "#EDF5EF", "#4F8862", title_font, body_font, pad=25)
    arrow(d, (575, 250), (1215, 250))
    centered_text(d, 895, 208, "Gửi public key QB", font(BOLD_PATH, 26), "#155E8A")
    arrow(d, (1225, 365), (585, 365), color="#648094")
    centered_text(d, 905, 376, "Gửi public key QA", font(BOLD_PATH, 26), "#526A7B")
    draw_card(d, (255, 515, 1545, 675), "Kết quả và giới hạn", ["ZA = dA × QB = dA × dB × G = dB × QA = ZB. ECDH chưa xác minh ai sở hữu public key; cần xác thực fingerprint/chứng chỉ."], "#FFF7E8", "#C38A2D", font(BOLD_PATH, 28), font(FONT_PATH, 25), pad=16)
    im.save(path)


def diagram_theory_hkdf(path: Path):
    im = Image.new("RGB", (1800, 590), "white")
    d = ImageDraw.Draw(im)
    title_font, body_font = font(BOLD_PATH, 31), font(FONT_PATH, 27)
    centered_text(d, 900, 30, "HKDF biến shared secret thành khóa theo đúng mục đích", font(BOLD_PATH, 40), "#123B5B")
    cards = [
        ((45, 145, 420, 365), "ECDH secret", ["Input keying material", "Chưa dùng trực tiếp làm AES key"], "#EAF4FA", "#2675A5"),
        ((490, 145, 890, 365), "HKDF-Extract", ["Đầu vào: salt + secret", "Đầu ra: pseudorandom key"], "#F1F5F8", "#66839A"),
        ((960, 145, 1360, 365), "HKDF-Expand", ["Ngữ cảnh info", "Độ dài L = 32 byte"], "#F1F5F8", "#66839A"),
        ((1430, 145, 1755, 365), "AES-256 key", ["Khóa đối xứng", "Dùng cho AES-GCM"], "#EDF5EF", "#4F8862"),
    ]
    for xy, title, lines, fill, outline in cards:
        draw_card(d, xy, title, lines, fill, outline, title_font, body_font, pad=20)
    for x1, x2 in [(420, 480), (890, 950), (1360, 1420)]: arrow(d, (x1, 255), (x2, 255))
    centered_text(d, 900, 425, "Salt không cần bí mật và được lưu cùng tin để người nhận dẫn xuất lại khóa.", font(BOLD_PATH, 25), "#526A7B")
    centered_text(d, 900, 475, "info gắn khóa với giao thức/hội thoại; dự án dùng HKDF-SHA256 và đầu ra 32 byte.", font(FONT_PATH, 25), "#526A7B")
    im.save(path)


def diagram_theory_aesgcm(path: Path):
    im = Image.new("RGB", (1800, 770), "white")
    d = ImageDraw.Draw(im)
    title_font, body_font = font(BOLD_PATH, 30), font(FONT_PATH, 26)
    centered_text(d, 900, 28, "AES-GCM mã hóa và xác thực toàn vẹn trong một thao tác", font(BOLD_PATH, 40), "#123B5B")
    top = [
        ((45, 135, 415, 340), "Đầu vào phía gửi", ["Plaintext", "AES key + nonce", "AAD (metadata xác thực)"], "#EAF4FA", "#2675A5"),
        ((515, 135, 875, 340), "AES-GCM encrypt", ["Mã hóa dữ liệu", "Tạo authentication tag"], "#F1F5F8", "#66839A"),
        ((975, 135, 1350, 340), "Gói tin lưu/gửi", ["Ciphertext + tag", "Nonce và AAD kèm theo"], "#EDF5EF", "#4F8862"),
        ((1450, 135, 1755, 340), "SQL Server", ["Lưu bytes", "Không có khóa giải mã"], "#F6FAFC", "#66839A"),
    ]
    for xy, title, lines, fill, outline in top:
        draw_card(d, xy, title, lines, fill, outline, title_font, body_font, pad=18)
    for x1, x2 in [(415, 505), (875, 965), (1350, 1440)]: arrow(d, (x1, 235), (x2, 235))
    draw_card(d, (300, 465, 920, 655), "Bên nhận xác minh trước", ["Dùng lại key, nonce và AAD đúng như lúc gửi", "Tag hợp lệ mới chấp nhận plaintext"], "#EAF4FA", "#2675A5", title_font, body_font, pad=20)
    draw_card(d, (1030, 465, 1545, 655), "Nếu kiểm tra thất bại", ["Sai key / tag / ciphertext / nonce / AAD", "Từ chối giải mã; không dùng plaintext"], "#FCEDEE", "#B64A4A", title_font, body_font, pad=20)
    arrow(d, (1165, 345), (790, 455), color="#648094")
    arrow(d, (920, 560), (1020, 560), color="#B64A4A")
    centered_text(d, 900, 700, "Nonce 12 byte phải duy nhất dưới cùng một khóa; AAD không bí mật nhưng được xác thực.", font(BOLD_PATH, 25), "#526A7B")
    im.save(path)


def diagram_theory_ecc_roles(path: Path):
    im = Image.new("RGB", (1800, 690), "white")
    d = ImageDraw.Draw(im)
    title_font, body_font = font(BOLD_PATH, 31), font(FONT_PATH, 27)
    centered_text(d, 900, 30, "Ba khái niệm ECC có mục đích khác nhau", font(BOLD_PATH, 40), "#123B5B")
    cards = [
        ((45, 140, 575, 510), "ECDH — thỏa thuận khóa", ["Thao tác: private key của mình + public key đối phương", "Kết quả: shared secret", "ChatBox: có dùng trước HKDF"], "#EAF4FA", "#2675A5"),
        ((635, 140, 1165, 510), "ECDSA — chữ ký số", ["Ký bằng private key", "Xác minh bằng public key", "Kết quả: kiểm tra nguồn gốc/toàn vẹn chữ ký"], "#FFF7E8", "#C38A2D"),
        ((1225, 140, 1755, 510), "ECIES — mã hóa kết hợp", ["Sơ đồ mã hóa khóa công khai", "Kết hợp KDF và mã hóa đối xứng", "Không tự ghép primitive để tạo sơ đồ mới"], "#EDF5EF", "#4F8862"),
    ]
    for xy, title, lines, fill, outline in cards:
        draw_card(d, xy, title, lines, fill, outline, title_font, body_font, pad=22)
    centered_text(d, 900, 570, "Luồng mã hóa tin nhắn của đồ án: ECDH → HKDF → AES-GCM.", font(BOLD_PATH, 29), "#155E8A")
    centered_text(d, 900, 615, "ECDH và ECDSA không phải thuật toán mã hóa nội dung tin nhắn.", font(FONT_PATH, 25), "#526A7B")
    im.save(path)


def diagram_theory_password_keys(path: Path):
    im = Image.new("RGB", (1800, 760), "white")
    d = ImageDraw.Draw(im)
    card_title, body_font = font(BOLD_PATH, 26), font(FONT_PATH, 23)
    centered_text(d, 900, 25, "Hai luồng dùng password trong project có mục đích và lưu trữ khác nhau", font(BOLD_PATH, 38), "#123B5B")
    d.rounded_rectangle((35, 110, 875, 665), radius=22, fill="#FFF8ED", outline="#C38A2D", width=4)
    d.rounded_rectangle((925, 110, 1765, 665), radius=22, fill="#EDF5EF", outline="#4F8862", width=4)
    centered_text(d, 455, 128, "A. Password tài khoản (server)", font(BOLD_PATH, 29), "#805614")
    centered_text(d, 1345, 128, "B. Password mở private-key file (client)", font(BOLD_PATH, 29), "#356343")
    left = [
        ((65, 205, 305, 420), "Password", ["Nhận tạm khi đăng ký/login"]),
        ((335, 205, 575, 420), "SHA-256", ["Một lượt", "Không salt (bản demo)"]),
        ((605, 205, 845, 420), "SQL Users", ["Lưu chuỗi hash", "Không lưu password rõ"]),
    ]
    right = [
        ((955, 205, 1195, 420), "Password", ["Chỉ nhập trên client"]),
        ((1225, 205, 1465, 420), "scrypt", ["Salt ngẫu nhiên", "N=2^15, r=8, p=1"]),
        ((1495, 205, 1735, 420), "AES-GCM file", ["Private key đã mã hóa", "Salt + nonce + ciphertext"]),
    ]
    for xy, title, lines in left:
        draw_card(d, xy, title, lines, "#FFFFFF", "#C38A2D", card_title, body_font, pad=16)
    for xy, title, lines in right:
        draw_card(d, xy, title, lines, "#FFFFFF", "#4F8862", card_title, body_font, pad=16)
    for a, b in [(305, 330), (575, 600), (1195, 1220), (1465, 1490)]: arrow(d, (a, 310), (b, 310), width=5)
    centered_text(d, 455, 475, "Hash nhanh: dễ bị đoán ngoại tuyến nếu database lộ.", font(BOLD_PATH, 23), "#A03C3C")
    centered_text(d, 455, 520, "Lựa chọn hiện tại của bản demo, không phải khuyến nghị sản phẩm.", font(FONT_PATH, 22), "#526A7B")
    centered_text(d, 1345, 475, "File cần salt và nonce để dẫn xuất/giải mã lại.", font(BOLD_PATH, 23), "#356343")
    centered_text(d, 1345, 520, "File khóa không nằm trong SQL; mất file thì không khôi phục từ server.", font(FONT_PATH, 22), "#526A7B")
    im.save(path)


def diagram_theory_tde(path: Path):
    im = Image.new("RGB", (1800, 660), "white")
    d = ImageDraw.Draw(im)
    title_font, body_font = font(BOLD_PATH, 29), font(FONT_PATH, 25)
    centered_text(d, 900, 30, "TDE dùng DEK để mã hóa dữ liệu SQL ở trạng thái lưu trữ", font(BOLD_PATH, 40), "#123B5B")
    cards = [
        ((45, 150, 435, 365), "Certificate SQL", ["Bảo vệ DEK", "Private key cần backup an toàn"], "#FFF7E8", "#C38A2D"),
        ((505, 150, 895, 365), "DEK", ["Database Encryption Key", "Khóa đối xứng của database"], "#F1F5F8", "#66839A"),
        ((965, 150, 1355, 365), "SQL data pages", ["Data files + log", "Backup database"], "#EAF4FA", "#2675A5"),
        ((1425, 150, 1755, 365), "Ổ đĩa / backup", ["Các page được mã hóa", "Khi lưu trữ"], "#EDF5EF", "#4F8862"),
    ]
    for xy, title, lines, fill, outline in cards:
        draw_card(d, xy, title, lines, fill, outline, title_font, body_font, pad=19)
    arrow(d, (435, 255), (495, 255), color="#C38A2D")
    arrow(d, (895, 255), (955, 255))
    arrow(d, (1355, 255), (1415, 255))
    centered_text(d, 900, 425, "Khi SQL Server chạy, engine mở DEK và giải mã page trong bộ nhớ để phục vụ truy vấn.", font(BOLD_PATH, 26), "#526A7B")
    draw_card(d, (255, 480, 1545, 610), "Phạm vi bảo vệ", ["TDE giảm rủi ro khi file database / log / backup bị lấy khỏi máy chủ; người có quyền truy vấn SQL vẫn đọc được giá trị mà engine đã mở."], "#FCEDEE", "#B64A4A", font(BOLD_PATH, 26), font(FONT_PATH, 23), pad=14)
    im.save(path)


def diagram_theory_layers(path: Path):
    im = Image.new("RGB", (1800, 650), "white")
    d = ImageDraw.Draw(im)
    title_font, body_font = font(BOLD_PATH, 29), font(FONT_PATH, 24)
    centered_text(d, 900, 28, "E2EE và TDE bảo vệ dữ liệu ở các giai đoạn khác nhau", font(BOLD_PATH, 40), "#123B5B")
    cards = [
        ((40, 145, 410, 360), "Client gửi", ["Plaintext trong UI", "Mã hóa trước HTTP"], "#EAF4FA", "#2675A5"),
        ((500, 145, 870, 360), "FastAPI", ["Nhận ciphertext", "Không có session key"], "#F1F5F8", "#66839A"),
        ((960, 145, 1330, 360), "SQL runtime", ["Query thấy ciphertext", "TDE trong suốt với query"], "#EDF5EF", "#4F8862"),
        ((1420, 145, 1760, 360), "Disk / backup", ["TDE mã hóa database pages", "DEK do certificate bảo vệ"], "#FFF7E8", "#C38A2D"),
    ]
    for xy, title, lines, fill, outline in cards:
        draw_card(d, xy, title, lines, fill, outline, title_font, body_font, pad=18)
    for x1, x2 in [(410, 490), (870, 950), (1330, 1410)]: arrow(d, (x1, 250), (x2, 250))
    d.rounded_rectangle((95, 415, 1320, 485), radius=18, fill="#E6F1F8", outline="#2675A5", width=3)
    centered_text(d, 707, 433, "E2EE: mã hóa ở client, giữ nội dung khỏi backend và truy vấn SQL", font(BOLD_PATH, 25), "#155E8A")
    d.rounded_rectangle((1085, 515, 1705, 585), radius=18, fill="#F7F0DF", outline="#C38A2D", width=3)
    centered_text(d, 1395, 533, "TDE: bảo vệ file SQL khi nằm trên ổ đĩa", font(BOLD_PATH, 25), "#805614")
    centered_text(d, 900, 610, "Hai lớp bổ sung cho nhau; TDE không thay mã hóa đầu cuối hay phân quyền truy vấn.", font(FONT_PATH, 24), "#526A7B")
    im.save(path)


def qn(tag):
    return f"{{{W}}}{tag}"


def make_run(text: str, bold=False, italic=False, code=False, size=None):
    run = etree.Element(qn("r"))
    props = etree.SubElement(run, qn("rPr"))
    if bold:
        etree.SubElement(props, qn("b"))
    if italic:
        etree.SubElement(props, qn("i"))
    if code:
        fonts = etree.SubElement(props, qn("rFonts"))
        fonts.set(qn("ascii"), "Consolas"); fonts.set(qn("hAnsi"), "Consolas")
    if size:
        etree.SubElement(props, qn("sz")).set(qn("val"), str(size))
    t = etree.SubElement(run, qn("t"))
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return run


def add_inline_runs(p, text: str):
    # Lightweight bold/code markup used only in this report's prose.
    pattern = re.compile(r"(\*\*.*?\*\*|`[^`]+`)")
    for item in pattern.split(text):
        if not item:
            continue
        if item.startswith("**") and item.endswith("**"):
            p.append(make_run(item[2:-2], bold=True))
        elif item.startswith("`") and item.endswith("`"):
            p.append(make_run(item[1:-1], code=True, size=19))
        else:
            p.append(make_run(item))


def make_paragraph(text="", style="Normal", page_break=False, align=None, first_line=None):
    p = etree.Element(qn("p"))
    pp = etree.SubElement(p, qn("pPr"))
    ps = etree.SubElement(pp, qn("pStyle")); ps.set(qn("val"), style)
    spacing = etree.SubElement(pp, qn("spacing")); spacing.set(qn("line"), "360"); spacing.set(qn("lineRule"), "auto")
    if page_break:
        etree.SubElement(pp, qn("pageBreakBefore"))
    if first_line is not None:
        ind = etree.SubElement(pp, qn("ind")); ind.set(qn("firstLine"), str(first_line))
    if align:
        etree.SubElement(pp, qn("jc")).set(qn("val"), align)
    if text:
        add_inline_runs(p, text)
    return p


def make_title(text, page_break=False):
    return make_paragraph(text, "Heading1", page_break=page_break, align="center")


def make_heading(text, level=2, page_break=False):
    style = {2: "Heading2", 3: "Heading3", 4: "Heading4"}[level]
    return make_paragraph(text, style, page_break=page_break)


def make_caption(text):
    p = make_paragraph(text, "Caption", align="center")
    p.find(qn("pPr")).append(etree.Element(qn("keepNext")))
    return p


def make_auto_field(instruction, fallback=""):
    p = make_paragraph("", "Normal")
    r = etree.SubElement(p, qn("r")); fc = etree.SubElement(r, qn("fldChar")); fc.set(qn("fldCharType"), "begin"); fc.set(qn("dirty"), "true")
    r = etree.SubElement(p, qn("r")); it = etree.SubElement(r, qn("instrText")); it.set("{http://www.w3.org/XML/1998/namespace}space", "preserve"); it.text = " " + instruction + " "
    r = etree.SubElement(p, qn("r")); etree.SubElement(r, qn("fldChar")).set(qn("fldCharType"), "separate")
    if fallback:
        p.append(make_run(fallback))
    r = etree.SubElement(p, qn("r")); etree.SubElement(r, qn("fldChar")).set(qn("fldCharType"), "end")
    return p


def make_sequence_caption(label, sequence, number, description):
    p = make_paragraph("", "Caption", align="center")
    pp = p.find(qn("pPr")); etree.SubElement(pp, qn("keepNext"))
    p.append(make_run(label + " "))
    r = etree.SubElement(p, qn("r")); etree.SubElement(r, qn("fldChar"), {qn("fldCharType"): "begin", qn("dirty"): "true"})
    r = etree.SubElement(p, qn("r")); instr = etree.SubElement(r, qn("instrText")); instr.set("{http://www.w3.org/XML/1998/namespace}space", "preserve"); instr.text = f" SEQ {sequence} \\* ARABIC "
    r = etree.SubElement(p, qn("r")); etree.SubElement(r, qn("fldChar"), {qn("fldCharType"): "separate"})
    p.append(make_run(str(number)))
    r = etree.SubElement(p, qn("r")); etree.SubElement(r, qn("fldChar"), {qn("fldCharType"): "end"})
    p.append(make_run(". " + description, italic=True, size=20))
    return p


def cell_paragraph(text, header=False):
    p = etree.Element(qn("p")); pp = etree.SubElement(p, qn("pPr")); etree.SubElement(pp, qn("pStyle")).set(qn("val"), "Normal")
    spacing = etree.SubElement(pp, qn("spacing")); spacing.set(qn("line"), "240"); spacing.set(qn("lineRule"), "auto")
    r = etree.SubElement(p, qn("r")); rp = etree.SubElement(r, qn("rPr"))
    fonts = etree.SubElement(rp, qn("rFonts")); fonts.set(qn("ascii"), "Times New Roman"); fonts.set(qn("hAnsi"), "Times New Roman")
    etree.SubElement(rp, qn("sz")).set(qn("val"), "18")
    if header: etree.SubElement(rp, qn("b"))
    t = etree.SubElement(r, qn("t")); t.text = str(text)
    return p


def make_table(rows):
    col_count = max(len(row) for row in rows)
    # Allocate wider columns to longer field/description cells.
    weights = [max(1, max(len(str(row[c])) for row in rows if c < len(row)) ** 0.55) for c in range(col_count)]
    if len(rows[0]) == 4 and col_count == 4:
        weights = [1.1, 2.2, 2.0, 2.0]
    total = sum(weights)
    widths = [int(TWIPS_WIDTH * w / total) for w in weights]
    widths[-1] += TWIPS_WIDTH - sum(widths)
    tbl = etree.Element(qn("tbl"))
    pr = etree.SubElement(tbl, qn("tblPr"))
    etree.SubElement(pr, qn("tblStyle")).set(qn("val"), "TableGrid")
    etree.SubElement(pr, qn("tblW"), {qn("w"): str(TWIPS_WIDTH), qn("type"): "dxa"})
    etree.SubElement(pr, qn("tblLayout")).set(qn("type"), "fixed")
    mar = etree.SubElement(pr, qn("tblCellMar"))
    for side, val in [("top", "80"), ("start", "100"), ("bottom", "80"), ("end", "100")]:
        etree.SubElement(mar, qn(side), {qn("w"): val, qn("type"): "dxa"})
    borders = etree.SubElement(pr, qn("tblBorders"))
    for side in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        etree.SubElement(borders, qn(side), {qn("val"): "single", qn("sz"): "5", qn("space"): "0", qn("color"): "9BAAB5"})
    grid = etree.SubElement(tbl, qn("tblGrid"))
    for width in widths: etree.SubElement(grid, qn("gridCol")).set(qn("w"), str(width))
    for ri, row in enumerate(rows):
        tr = etree.SubElement(tbl, qn("tr"))
        trpr = etree.SubElement(tr, qn("trPr"))
        if ri == 0:
            etree.SubElement(trpr, qn("tblHeader"))
        for ci in range(col_count):
            tc = etree.SubElement(tr, qn("tc")); tcp = etree.SubElement(tc, qn("tcPr"))
            etree.SubElement(tcp, qn("tcW"), {qn("w"): str(widths[ci]), qn("type"): "dxa"})
            if ri == 0:
                shd = etree.SubElement(tcp, qn("shd")); shd.set(qn("val"), "clear"); shd.set(qn("color"), "auto"); shd.set(qn("fill"), "DCEAF3")
            tc.append(cell_paragraph(row[ci] if ci < len(row) else "", header=(ri == 0)))
        # Prevent rows from splitting when possible.
        etree.SubElement(trpr, qn("cantSplit"))
    return tbl


def make_figure(path: Path, rel_id: str, name: str, descr: str, drawing_id: int):
    p = make_paragraph("", "Normal", align="center")
    etree.SubElement(p.find(qn("pPr")), qn("keepNext"))
    run = etree.SubElement(p, qn("r")); drawing = etree.SubElement(run, qn("drawing"))
    inline = etree.SubElement(drawing, f"{{{WP}}}inline", {"distT": "0", "distB": "0", "distL": "0", "distR": "0"})
    width = 5_700_000
    image = Image.open(path)
    height = int(width * image.height / image.width)
    etree.SubElement(inline, f"{{{WP}}}extent", {"cx": str(width), "cy": str(height)})
    etree.SubElement(inline, f"{{{WP}}}effectExtent", {"l": "0", "t": "0", "r": "0", "b": "0"})
    etree.SubElement(inline, f"{{{WP}}}docPr", {"id": str(drawing_id), "name": name, "descr": descr})
    frame = etree.SubElement(inline, f"{{{WP}}}cNvGraphicFramePr"); etree.SubElement(frame, f"{{{A}}}graphicFrameLocks", {"noChangeAspect": "1"})
    graphic = etree.SubElement(inline, f"{{{A}}}graphic"); gd = etree.SubElement(graphic, f"{{{A}}}graphicData", {"uri": PIC})
    pic = etree.SubElement(gd, f"{{{PIC}}}pic")
    nv = etree.SubElement(pic, f"{{{PIC}}}nvPicPr"); etree.SubElement(nv, f"{{{PIC}}}cNvPr", {"id": str(drawing_id), "name": name, "descr": descr}); etree.SubElement(nv, f"{{{PIC}}}cNvPicPr")
    fill = etree.SubElement(pic, f"{{{PIC}}}blipFill"); etree.SubElement(fill, f"{{{A}}}blip", {f"{{{R}}}embed": rel_id}); stretch = etree.SubElement(fill, f"{{{A}}}stretch"); etree.SubElement(stretch, f"{{{A}}}fillRect")
    sp = etree.SubElement(pic, f"{{{PIC}}}spPr"); xfrm = etree.SubElement(sp, f"{{{A}}}xfrm"); etree.SubElement(xfrm, f"{{{A}}}off", {"x": "0", "y": "0"}); etree.SubElement(xfrm, f"{{{A}}}ext", {"cx": str(width), "cy": str(height)})
    geom = etree.SubElement(sp, f"{{{A}}}prstGeom", {"prst": "rect"}); etree.SubElement(geom, f"{{{A}}}avLst")
    return p


def add_content_type(ct_root):
    if not any(e.get("Extension") == "png" for e in ct_root.findall(f"{{{CT}}}Default")):
        etree.SubElement(ct_root, f"{{{CT}}}Default", {"Extension": "png", "ContentType": "image/png"})


def main():
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper()
    if source_hash != "8986E37CC42DC20182CB07DE4D1DDD502AB64D7B1AB8249511F4BCCB1541A7B2":
        raise RuntimeError("Reference DOCX changed since inspection; redistill before editing")
    with ZipFile(SOURCE) as zin:
        parts = {name: zin.read(name) for name in zin.namelist()}
    parser = etree.XMLParser(remove_blank_text=False)
    doc = etree.fromstring(parts["word/document.xml"], parser)
    body_elem = doc.find(f"{{{W}}}body")
    children = list(body_elem)
    cover_nodes = []
    for child in children:
        if etree.QName(child).localname in {"bookmarkStart", "sdt", "bookmarkEnd"} and len(cover_nodes) < 4:
            cover_nodes.append(child)
        else:
            break
    if len(cover_nodes) != 4 or sum(etree.QName(x).localname == "sdt" for x in cover_nodes) != 2:
        raise RuntimeError("Could not locate the two preserved cover controls")
    cover_xml_before = [etree.tostring(x, method="c14n") for x in cover_nodes]
    section_break = None
    final_sect = body_elem.find(f"{{{W}}}sectPr")
    for child in children:
        if etree.QName(child).localname == "p" and child.find(f"{{{W}}}pPr/{{{W}}}sectPr") is not None:
            section_break = copy.deepcopy(child.find(f"{{{W}}}pPr/{{{W}}}sectPr"))
    if section_break is None or final_sect is None:
        raise RuntimeError("Expected front-matter boundary and final section properties")
    base_paragraphs = doc.xpath("//w:p", namespaces=NS)
    def find_template(text):
        for p in base_paragraphs:
            if "".join(p.xpath(".//w:t/text()", namespaces=NS)).strip() == text:
                return p
        raise RuntimeError("Paragraph style exemplar not found: " + text)
    exemplars = {
        "Normal": find_template("Để hoàn thành đồ án môn học Bảo mật thông tin với đề tài: “Nghiên cứu và xây dựng giải pháp bảo mật cơ sở dữ liệu SQL kết hợp kỹ thuật mã hóa dựa trên mật mã đường cong elliptic (ECC)”, bên cạnh sự nỗ lực của bản thân, em đã nhận được sự hỗ trợ, hướng dẫn tận tình từ phía Nhà trường và các Thầy/Cô."),
        "Heading1": find_template("LỜI MỞ ĐẦU"),
        "Heading2": find_template("Tổng quan về vấn đề được nghiên cứu"),
        "Heading3": find_template("Ưu điểm"),
    }
    # Retain template paragraph properties while creating clean replacement paragraphs.
    def template_p(style, text="", page_break=False, align=None, first_line=None):
        exemplar = exemplars.get(style)
        p = etree.Element(f"{{{W}}}p")
        if exemplar is not None and exemplar.find(f"{{{W}}}pPr") is not None:
            pp = copy.deepcopy(exemplar.find(f"{{{W}}}pPr"))
            for node in list(pp):
                if etree.QName(node).localname in {"sectPr", "pageBreakBefore", "framePr"}:
                    pp.remove(node)
        else:
            pp = etree.Element(f"{{{W}}}pPr")
        ps = pp.find(f"{{{W}}}pStyle")
        if ps is None: ps = etree.SubElement(pp, f"{{{W}}}pStyle")
        ps.set(f"{{{W}}}val", style)
        if page_break: etree.SubElement(pp, f"{{{W}}}pageBreakBefore")
        if align:
            jc = pp.find(f"{{{W}}}jc")
            if jc is None: jc = etree.SubElement(pp, f"{{{W}}}jc")
            jc.set(f"{{{W}}}val", align)
        if first_line is not None:
            ind = pp.find(f"{{{W}}}ind")
            if ind is None: ind = etree.SubElement(pp, f"{{{W}}}ind")
            ind.set(f"{{{W}}}firstLine", str(first_line))
        if not pp.findall(f"{{{W}}}spacing"):
            etree.SubElement(pp, f"{{{W}}}spacing", {f"{{{W}}}line": "360", f"{{{W}}}lineRule": "auto"})
        p.append(pp)
        if text: add_inline_runs(p, text)
        return p

    # Rebind paragraph builders to source-derived formatting.
    def heading(text, level=2, page_break=False):
        return template_p({1:"Heading1",2:"Heading2",3:"Heading3"}[level], text, page_break, "center" if level == 1 else None)
    def title(text, page_break=False):
        return template_p("Heading1", text, page_break, "center")
    def body(text):
        return template_p("Normal", text, first_line="360")
    def bullet(text):
        p=body("• " + text)
        pp=p.find(f"{{{W}}}pPr")
        ind=pp.find(f"{{{W}}}ind")
        if ind is None: ind=etree.SubElement(pp,f"{{{W}}}ind")
        ind.set(f"{{{W}}}left","360"); ind.set(f"{{{W}}}hanging","240")
        return p
    def caption(text):
        p=template_p("Normal", text, align="center")
        pp=p.find(f"{{{W}}}pPr")
        etree.SubElement(pp, f"{{{W}}}keepNext")
        for r in p.findall(f"{{{W}}}r"):
            for el in list(r):
                if etree.QName(el).localname=="rPr":
                    etree.SubElement(el,f"{{{W}}}i")
                    etree.SubElement(el,f"{{{W}}}sz").set(f"{{{W}}}val","20")
        return p
    def table(rows):
        return make_table(rows)

    diagram_architecture(MEDIA / "architecture.png")
    diagram_flow(MEDIA / "message_flow.png")
    diagram_erd(MEDIA / "erd.png")
    diagram_theory_ecdh(MEDIA / "theory_ecdh.png")
    diagram_theory_hkdf(MEDIA / "theory_hkdf.png")
    diagram_theory_aesgcm(MEDIA / "theory_aesgcm.png")
    diagram_theory_ecc_roles(MEDIA / "theory_ecc_roles.png")
    diagram_theory_password_keys(MEDIA / "theory_password_keys.png")
    diagram_theory_tde(MEDIA / "theory_tde.png")
    diagram_theory_layers(MEDIA / "theory_layers.png")
    figure_names = [
        "architecture.png", "message_flow.png", "erd.png", "theory_ecdh.png",
        "theory_hkdf.png", "theory_aesgcm.png", "theory_ecc_roles.png",
        "theory_password_keys.png", "theory_tde.png", "theory_layers.png",
    ]

    relroot = etree.fromstring(parts["word/_rels/document.xml.rels"], parser)
    rel_ids = []
    for rel in relroot:
        match = re.fullmatch(r"rId(\d+)", rel.get("Id", ""))
        if match: rel_ids.append(int(match.group(1)))
    next_id = max(rel_ids, default=0) + 1
    image_rels = {}
    for idx, name in enumerate(figure_names, start=1):
        rid = f"rId{next_id}"; next_id += 1
        image_rels[name] = rid
        etree.SubElement(relroot, f"{{{PKG_REL}}}Relationship", {"Id": rid, "Type": R + "/image", "Target": "media/" + name})
        parts["word/media/" + name] = (MEDIA / name).read_bytes()
    types = etree.fromstring(parts["[Content_Types].xml"], parser); add_content_type(types)
    parts["[Content_Types].xml"] = etree.tostring(types, xml_declaration=True, encoding="UTF-8", standalone=True)
    parts["word/_rels/document.xml.rels"] = etree.tostring(relroot, xml_declaration=True, encoding="UTF-8", standalone=True)

    # Construct front matter. The retained front-matter section uses Roman page numbering.
    new_body = list(cover_nodes)
    new_body.append(title("LỜI MỞ ĐẦU", page_break=True))
    for _, text in PREFACE: new_body.append(body(text))
    new_body.append(title("LỜI CẢM ƠN", page_break=True))
    for text in THANKS: new_body.append(body(text))
    new_body.append(title("NHIỆM VỤ ĐỒ ÁN", page_break=True))
    new_body.append(body("Đề tài: Nghiên cứu và xây dựng giải pháp bảo mật cơ sở dữ liệu SQL kết hợp kỹ thuật mã hóa dựa trên mật mã đường cong elliptic (ECC)."))
    for item in TASKS: new_body.append(bullet(item))
    new_body.append(title("NHẬN XÉT CỦA GIẢNG VIÊN", page_break=True))
    for _ in range(8): new_body.append(body("........................................................................................................................................................................................"))
    new_body.append(title("MỤC LỤC", page_break=True))
    new_body.append(make_auto_field('TOC \\o "1-3" \\h \\z \\u', ""))
    new_body.append(title("DANH MỤC HÌNH", page_break=True))
    new_body.append(make_auto_field('TOC \\c "Hinh" \\h \\z', ""))
    new_body.append(title("DANH MỤC BẢNG", page_break=True))
    new_body.append(make_auto_field('TOC \\c "Bang" \\h \\z', ""))
    front_boundary = etree.Element(f"{{{W}}}p")
    ppr = etree.SubElement(front_boundary, f"{{{W}}}pPr"); ppr.append(copy.deepcopy(section_break))
    new_body.append(front_boundary)

    # The Arabic-numbered content section starts from page 1.
    figure_specs = {
        "architecture.png": ("Sơ đồ kiến trúc tổng thể", "Sơ đồ thể hiện client mã hóa, backend chỉ lưu và SQL Server TDE"),
        "message_flow.png": ("Luồng xử lý message", "Luồng ECDH, HKDF, AES-GCM, lưu SQL và giải mã"),
        "erd.png": ("ERD ChatBox", "Sơ đồ quan hệ Users, Conversations, ConversationMembers và Messages"),
        "theory_ecdh.png": ("Mô hình thỏa thuận khóa ECDH", "Hai client tính ra cùng bí mật chung từ khóa riêng cục bộ và public key của bên kia"),
        "theory_hkdf.png": ("Hai giai đoạn Extract và Expand của HKDF", "HKDF sử dụng shared secret, salt và thông tin ngữ cảnh để tạo khóa AES 32 byte"),
        "theory_aesgcm.png": ("Mã hóa và xác thực bằng AES-GCM", "Ciphertext và tag được xác minh trước khi bên nhận chấp nhận plaintext"),
        "theory_ecc_roles.png": ("Phân biệt ECDH, ECDSA và ECIES", "So sánh mục đích, thao tác khóa và kết quả của ba cơ chế ECC"),
        "theory_password_keys.png": ("Luồng password tài khoản và private-key file", "Phân biệt SHA-256 của tài khoản với scrypt và AES-GCM bảo vệ private key cục bộ"),
        "theory_tde.png": ("Chuỗi khóa và phạm vi bảo vệ của TDE", "Certificate bảo vệ DEK, DEK mã hóa các trang SQL tại trạng thái lưu trữ"),
        "theory_layers.png": ("Phạm vi bảo vệ E2EE và TDE", "E2EE bảo vệ nội dung qua API và SQL, TDE mã hóa file database trên đĩa"),
    }
    drawing_id = 1
    table_id = 1
    for chapter_title, blocks in CHAPTERS:
        new_body.append(title(chapter_title, page_break=True))
        for typ, value in blocks:
            if typ == "h2": new_body.append(heading(value, 2))
            elif typ == "h3": new_body.append(heading(value, 3))
            elif typ == "body": new_body.append(body(value))
            elif typ == "bullet": new_body.append(bullet(value))
            elif typ == "table":
                desc = value[0][0] + " - " + value[0][-1]
                new_body.append(make_sequence_caption("Bảng", "Bang", table_id, desc))
                new_body.append(table(value))
                table_id += 1
            elif typ == "figure":
                name=value; image_path=MEDIA/name; rel_id=image_rels[name]
                descr=figure_specs[name][1]
                new_body.append(make_figure(image_path, rel_id, figure_specs[name][0], descr, drawing_id)); drawing_id+=1
                new_body.append(make_sequence_caption("Hình", "Hinh", drawing_id-1, figure_specs[name][0]))
            elif typ == "caption":
                # The descriptive line follows the actual image caption for clarity.
                pass
            else: raise ValueError("unknown block kind " + typ)
    new_body.append(title("TÀI LIỆU THAM KHẢO", page_break=True))
    for i, ref in enumerate(REFERENCES, start=1):
        p=body(f"[{i}] {ref}")
        pp=p.find(f"{{{W}}}pPr")
        ind=pp.find(f"{{{W}}}ind")
        if ind is None: ind=etree.SubElement(pp,f"{{{W}}}ind")
        ind.set(f"{{{W}}}left","360"); ind.set(f"{{{W}}}hanging","360")
        new_body.append(p)

    # Preserve the final section properties from the source package.
    for child in list(body_elem): body_elem.remove(child)
    for child in new_body: body_elem.append(child)
    body_elem.append(final_sect)

    # Turn on Word field refresh so TOC and lists can be populated when opened.
    settings = etree.fromstring(parts["word/settings.xml"], parser)
    upd = settings.find(f"{{{W}}}updateFields")
    if upd is None: upd = etree.SubElement(settings, f"{{{W}}}updateFields")
    upd.set(f"{{{W}}}val", "true")
    parts["word/settings.xml"] = etree.tostring(settings, xml_declaration=True, encoding="UTF-8", standalone=True)

    # Update core title and the visible author metadata only; cover content is preserved.
    if "docProps/core.xml" in parts:
        core=etree.fromstring(parts["docProps/core.xml"], parser)
        dc_title="{http://purl.org/dc/elements/1.1/}title"
        el=core.find(dc_title)
        if el is not None: el.text="Bảo mật cơ sở dữ liệu SQL kết hợp ECC"
        parts["docProps/core.xml"]=etree.tostring(core,xml_declaration=True,encoding="UTF-8",standalone=True)

    # Ensure the retained cover controls survived byte-for-byte at the XML node level.
    out_doc = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
    reparsed = etree.fromstring(out_doc, parser)
    final_body=reparsed.find(f"{{{W}}}body")
    for before, after in zip(cover_xml_before, list(final_body)[:4]):
        if before != etree.tostring(after,method="c14n"):
            raise RuntimeError("Cover XML changed during body replacement")
    parts["word/document.xml"] = out_doc

    # Remove obsolete embedded screenshots from the previous shop project, while
    # retaining every image relationship used by the preserved covers or new figures.
    used_rids = set()
    for part_name, data in list(parts.items()):
        if part_name.endswith(".xml") and not part_name.endswith(".rels"):
            try:
                xml = etree.fromstring(data, parser)
            except etree.XMLSyntaxError:
                continue
            for value in xml.xpath("//@r:id | //@r:embed | //@r:link", namespaces=NS):
                used_rids.add(value)
    for rel in list(relroot):
        if rel.get("Type", "").endswith("/image") and rel.get("Id") not in used_rids:
            target = "word/" + rel.get("Target", "")
            parts.pop(target, None)
            relroot.remove(rel)
    live_media = {"word/" + rel.get("Target", "") for rel in relroot if rel.get("Type", "").endswith("/image")}
    for name in list(parts):
        if name.startswith("word/media/") and name not in live_media:
            parts.pop(name, None)
    parts["word/_rels/document.xml.rels"] = etree.tostring(relroot, xml_declaration=True, encoding="UTF-8", standalone=True)
    # Update app.xml basic stats to prevent stale previous-project word counts.
    if "docProps/app.xml" in parts:
        app=etree.fromstring(parts["docProps/app.xml"], parser)
        nsapp={"ep":"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"}
        for tag, value in [("Paragraphs", str(len(new_body)))]:
            el=app.find(f"{{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}}{tag}")
            if el is not None: el.text=value
        # Remove stale counts from the previous draft; Word will recalculate on save.
        for tag in ["Words", "Characters", "CharactersWithSpaces", "Pages"]:
            el=app.find(f"{{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}}{tag}")
            if el is not None: app.remove(el)
        parts["docProps/app.xml"]=etree.tostring(app,xml_declaration=True,encoding="UTF-8",standalone=True)

    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as zout:
        for name, data in parts.items(): zout.writestr(name, data)
    print("Prepared", OUTPUT)
    print("source_sha256", source_hash)
    print("body elements", len(new_body), "chapters", len(CHAPTERS), "references", len(REFERENCES))
    print("cover_controls_preserved", len(cover_xml_before))


if __name__ == "__main__":
    main()
