# ChatBox

## Mục đích tài liệu

Tài liệu này cung cấp ngữ cảnh thống nhất cho AI hỗ trợ phát triển ChatBox và viết báo cáo đồ án. Khi viết nội dung, hãy phân biệt rõ:

- **Thiết kế đã thống nhất** với **chức năng đã được triển khai**.
- Bảo vệ SQL khi lưu trữ với mã hóa đầu cuối cho tin nhắn.
- ECC/ECDH, ECDSA và AES-GCM.
- Giới hạn bảo mật hiện tại với mục tiêu thiết kế.

Không khẳng định tính năng đã hoạt động nếu chưa có code hoặc kết quả kiểm thử xác nhận.

## Đề tài và mục tiêu

Đề tài: **Nghiên cứu và xây dựng giải pháp bảo mật dữ liệu trong cơ sở dữ liệu SQL kết hợp mật mã đường cong elliptic (ECC)**.

Ứng dụng minh họa là chat 1-1 viết bằng Python. Hướng lưu trữ dự kiến là **Microsoft SQL Server** để có thể sử dụng Transparent Data Encryption (TDE). VS Code là môi trường soạn thảo và phát triển; SQL Server là hệ quản trị cơ sở dữ liệu chạy riêng, có thể đặt trên cùng máy phát triển.

## Hai lớp bảo vệ cần trình bày riêng

### 1. Mã hóa tin nhắn ở cấp ứng dụng

Luồng dự kiến:

1. Hai client có cặp khóa ECC.
2. Client dùng ECDH để tạo bí mật chung.
3. HKDF-SHA256 dẫn xuất khóa phiên/tin nhắn từ bí mật ECDH và salt.
4. AES-256-GCM mã hóa nội dung và xác thực toàn vẹn.
5. Backend lưu và chuyển tiếp ciphertext cùng metadata; không giải mã nội dung.

Private key, bí mật ECDH, khóa AES và plaintext không được lưu vào SQL.

### 2. TDE trong SQL Server

TDE mã hóa database files và transaction log khi nằm trên ổ đĩa; SQL Server tự giải mã khi xử lý truy vấn. TDE bảo vệ dữ liệu lưu trữ và backup trong những tình huống thích hợp, nhưng **không phải mã hóa riêng từng dòng hoặc từng cột**. Nó không ngăn người có quyền truy vấn SQL đọc dữ liệu khi database đang chạy, cũng không thay thế phân quyền, bảo vệ ứng dụng, bảo vệ kết nối mạng hoặc mã hóa cấp ứng dụng.

Cần quản lý và sao lưu certificate/key dùng cho TDE an toàn, tách khỏi bản sao database. Mất certificate/key có thể khiến không khôi phục được dữ liệu.

Trong project, `sql/tde_setup.sql` là script quản trị chạy một lần trong SSMS
để tạo master key/certificate, backup certificate và private key, tạo DEK AES-256
rồi bật TDE cho `ChatBox`. Thay các giá trị `REPLACE_WITH_*` bằng thông tin thật
trước khi chạy; không commit mật khẩu hoặc file backup certificate vào Git. Đường
dẫn backup là đường dẫn trên máy SQL Server và tài khoản dịch vụ SQL Server cần
quyền ghi vào thư mục đó. `database/db.py` chỉ kiểm tra `sys.databases.is_encrypted`
và cảnh báo khi TDE chưa bật; tài khoản ứng dụng không cần quyền tạo key/certificate
hay bật TDE. Trạng thái `is_encrypted = 1` cho biết TDE đã bật, còn encryption scan
có thể vẫn đang chạy; xem `sys.dm_database_encryption_keys.encryption_state` để
xác nhận `3` (đã mã hóa hoàn tất).

Nếu cần mã hóa một cột để database engine không thấy plaintext, đó là yêu cầu khác, cần nghiên cứu cơ chế như Always Encrypted hoặc mã hóa ở tầng ứng dụng. Đây chưa phải phần đã thống nhất của bản demo.

## Thuật toán và vai trò

- **ECDH trên P-256**: hai bên tạo bí mật chung. ECDH không trực tiếp mã hóa tin nhắn.
- **HKDF-SHA256**: dẫn xuất khóa AES từ bí mật ECDH; không dùng bí mật ECDH trực tiếp làm khóa.
- **AES-256-GCM**: mã hóa và xác thực tin nhắn. Mỗi lần mã hóa phải dùng nonce mới, không lặp nonce với cùng khóa.
- **ECDSA**: chỉ dùng ký và xác minh chữ ký nếu giao thức cần xác thực khóa hoặc thông điệp. Không dùng ECDSA để mã hóa/giải mã.
- **SHA-256 cho mật khẩu**: chủ dự án hiện muốn dùng một lượt SHA-256 để lưu password và giới hạn số lần đăng nhập. Đây là quyết định phạm vi hiện tại, nhưng phải nêu rõ giới hạn: SHA-256 thuần rất nhanh, nên nếu hash bị lộ qua truy cập SQL hoặc bản dump đã giải mã, password có thể bị đoán ngoại tuyến. Rate limit chỉ giới hạn thử đăng nhập trực tuyến, không làm chậm đoán ngoại tuyến. Đây không phải khuyến nghị bảo mật password; báo cáo phải ghi rõ rủi ro. TDE không khắc phục điểm yếu thuật toán hash nếu attacker lấy được hash.
- **TDE**: mã hóa dữ liệu SQL Server ở trạng thái lưu trữ; không thay thế mã hóa tin nhắn AES-GCM.

Không tự thiết kế ECIES hoặc thuật toán mật mã mới. Dùng thư viện mật mã chuẩn.

## Dữ liệu dự kiến trong SQL Server

Tên bảng và kiểu dữ liệu có thể điều chỉnh khi triển khai.

### `Users`

- `UserId`
- `Username`
- `PasswordHash`
- `CreatedAt`

Không lưu password rõ.

### `PublicKeys`

- `UserId`
- `KeyVersion`
- `PublicKey`
- `Status`
- `CreatedAt` / thời điểm thu hồi

Server có thể làm danh bạ public key. Lưu public key không tự xác minh danh tính chủ khóa; cần chọn cơ chế xác minh như fingerprint hoặc chữ ký/chứng chỉ.

### `Conversations` và `ConversationMembers`

Dùng ID hội thoại riêng, chẳng hạn UUID, không tạo `conversation_id` bằng cách ghép username. Bảng thành viên ánh xạ user với conversation. Backend phải kiểm tra quyền thành viên trước khi đọc hoặc gửi tin.

### `Messages`

- `MessageId`
- `ConversationId`
- `SenderId`
- `Ciphertext`
- `Nonce`
- `HkdfSalt`
- `Aad`
- `KeyVersion`
- `ProtocolVersion`
- `CreatedAt`

Với API `AESGCM` của thư viện `cryptography`, ciphertext trả về thường đã nối tag xác thực ở cuối; nếu dùng cách này không cần cột tag riêng. `Nonce`, salt và AAD không phải bí mật nhưng cần có để bên nhận xác minh/giải mã. Các bytes có thể lưu dưới dạng `VARBINARY`; khóa công khai DER cũng có thể lưu dạng nhị phân.

Không lưu plaintext, private key, bí mật ECDH hoặc khóa AES phiên trong SQL hay log.

## Workflow backend 1-1 dự kiến

1. Đăng ký tài khoản: lưu username và password hash; không lưu password rõ.
2. Đăng ký/đổi public key: lưu public key theo user và phiên bản.
3. Tạo conversation: sinh ID riêng, thêm hai thành viên.
4. Tra cứu khóa: client lấy public key đối phương; khóa cần được xác minh bằng cơ chế tin cậy đã chọn.
5. Thiết lập bí mật: hai client chạy ECDH rồi HKDF.
6. Gửi tin: client tạo nonce mới, mã hóa bằng AES-GCM và gửi ciphertext, nonce, salt, AAD cùng metadata.
7. Nhận tin: server kiểm tra quyền, lưu hoặc chuyển tiếp gói mã hóa mà không giải mã.
8. Đọc tin: server chỉ trả bản ghi cho thành viên; client dựng khóa, xác minh tag rồi giải mã.
9. TDE bảo vệ database files/log/backup khi lưu trên SQL Server; phân quyền, logging an toàn và bảo vệ certificate vẫn cần thiết.

Tin nhắn được lưu vào `dbo.Messages` ngay khi người gửi gọi `POST /messages`, không
phụ thuộc người nhận có đang đăng nhập hay không. `GET /conversations` liệt kê các
hội thoại đã lưu cho người dùng sau khi đăng nhập; khi mở một hội thoại, client gọi
`GET /conversations/{conversation_id}/messages` để tải lịch sử ciphertext và giải
mã bằng private key cục bộ. Client lấy public key khi mở chat; các lần cập nhật
định kỳ dùng `after_id` để chỉ tải tin có ID mới hơn, không tải lại toàn bộ lịch sử.
Sidebar client cung cấp danh sách hội thoại và tìm username đã đăng ký để mở chat
mới; backend không cần presence/online status để lưu hoặc giao lại lịch sử. Người
nhận vẫn cần giữ đúng private key để đọc nội dung.

## Giới hạn giao thức hiện tại

Thiết kế static ECDH với khóa dài hạn là bản đơn giản cho chat 1-1; chưa có forward secrecy như các giao thức chat hiện đại. Đổi public key có thể ảnh hưởng khả năng giải mã lịch sử. Cần định nghĩa rõ lưu trữ/backup private key và quy trình xoay/thu hồi khóa trước khi tuyên bố hệ thống hoàn chỉnh.

Nhóm chat và nhiều thiết bị chưa nằm trong phạm vi bản đầu. Không thể dùng nguyên xi một shared key ECDH của 1-1 cho nhóm nhiều người.

## Cấu trúc dự án tham khảo

```text
ChatBox/
├── client/
│   ├── ui/
│   └── main.py
├── server/
│   ├── api.py
│   └── main.py
├── cipher/
│   ├── ecc/
│   │   ├── key_agreement.py
│   │   └── key_storage.py
│   ├── encryption.py
│   └── __init__.py
├── database/
│   ├── models.py
│   ├── db.py
│   └── repositories.py
├── sql/
│   └── schema.sql
├── tests/
├── requirements.txt
└── README.md
```

Mã hóa/giải mã tin nhắn thuộc phía client. Server xử lý xác thực, phân quyền, public-key directory, lưu trữ và chuyển tiếp. `database/db.py` kết nối SQL Server; `repositories.py` chứa truy vấn tham số; `schema.sql` mô tả schema và migration ban đầu.
