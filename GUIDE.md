# Tạo scene 3D bằng AI — hướng dẫn cho người không rành kỹ thuật

Ngày 2026-11-02 · Repo: `hpbaoan-source/threejs-scene-gen` · Model: `MiniMax-M3.1-Flash`

---

## 1. Bản chất thật: đây KHÔNG phải "AI vẽ ảnh 3D"

Đây là chỗ dễ hiểu sai nhất, nên em nói trước.

Ảnh scene **không phải ảnh được vẽ ra**. Chúng là **chương trình máy tính** — AI viết ra code
JavaScript (mỗi scene ~1.100 dòng, ~33KB), rồi trình duyệt mở file code đó lên và **tự vẽ lại
3D trong lúc anh di chuột, 60 lần mỗi giây**. Đúng cơ chế của mọi game 3D.

Hệ quả trực tiếp:

| | Ảnh vẽ sẵn | Scene do AI viết code |
|---|---|---|
| Đổi màu đèn / vị trí đèn | Phải vẽ lại từ đầu | Sửa **1 dòng code** |
| Xoay camera 360° | Không có | Có sẵn, tự viết tay |
| Đưa vào web/app | Phải xuất file `.glb`/`.fbx` | Nhúng thẳng file HTML |
| Kích thước | 5–50 MB (kèm texture) | **33 KB** |
| Chỉnh sửa bởi người không biết code | Không | Không — **nhưng chỉ cần sửa prompt** |

Nói cách khác: anh đang **điều khiển một người họa sĩ 3D cực nhanh** bằng cách viết yêu cầu bằng lời.

---

## 2. Hai chế độ

### Chế độ 1 — One-shot: 1 lệnh, ~$0.005

```bash
python3 make_scene.py --mode oneshot "a Japanese village at dusk with glowing lanterns" \
                       --out scenes/village.html
```

Một lần gọi model, ra một file HTML. **Không kiểm chứng gì cả** — file đó là đúng những gì model
viết ra, không qua đáy nào.

### Chế độ 2 — Repair loop: sinh → render → model phê bích → sửa → lặp

```bash
python3 make_scene.py --mode repair --repair 3 --threshold 7 "an Apollo spacecraft on its launch pad"
```

Một scene chỉ được **chấp nhận** khi cả 3 điều đúng:
1. Không có lỗi console
2. Không vượt qua "cổng chất lượng" tự động (ảnh quá tối / quá sáng / phẳng)
3. Người phê bích (cũng là AI) chấm điểm ≥ threshold và trả lời `pass`

Toàn bộ lịch sử được ghi vào `history.json`.

---

## 3. Quy trình chi tiết (5 bước, tổng ~2 phút cho one-shot)

1. **Viết mô tả** — 1–3 câu tiếng Anh. Càng có chi tiết cụ thể ("dawn", "xenon floodlights",
   "steam venting from the flame trench") thì kết quả càng đúng ý.
2. **Model sinh ra file HTML** — 33KB, 1.100 dòng, kèm tiêu đề, HUD, điều khiển chuột.
3. **Mở bằng trình duyệt headless** (Chromium không hiện cửa sổ) → bắt lỗi console, đo độ sáng ảnh,
   chụp ảnh 1280×720.
4. **Model nhìn ảnh** → trả về: điểm số, vấn đề nhìn thấy, và chỉ dẫn sửa cụ thể.
5. **Sửa code theo chỉ dẫn → render lại** → lặp tới khi đạt chuẩn.

Bước 4 là phần mới so với bản one-shot, và là lý do loop repair tốn hơn.

---

## 4. Ba nguyên tắc làm cho vòng lặp đáng tin

**1. Script lo phần cơ học, model chỉ lo phần phán đoán.**
Python lo render, đo, vá file. Model chỉ nhìn **một ảnh** rồi trả lời pass/fail — nó không tự
sửa code. Nhờ vậy mỗi vòng tiêu tốn rất ít token.

**2. Chặn sớm, trước khi mở trình duyệt.**
File bị cắt cụt, thiếu canvas, thẻ `<script>` không khớp → script loại ngay, **không tốn token
gọi model**. Cùng nguyên tắc với img2threejs: *"geometric gates run before the browser does"*.

**3. Cổng chất lượng tự động trên ảnh.**
Ảnh gần như đen (meanLuma < 0.06), ảnh cháy trắng, hoặc ảnh phẳng không có chiều sâu → script tự
loại, **không cần hỏi model**. Chính cổng này bắt được lỗi "scene bị tối" mà bản one-shot bỏ lọt.

---

## 5. Chất lượng thật — đo bằng ảnh, không bằng lời quảng cáo

Một ví dụ đo thật (prompt: "a red cube on a grey ground plane, well lit, soft shadows"):

| Vòng | Điểm | Vấn đề còn lại |
|---|---|---|
| 0 (one-shot) | 6/10 | 5 lỗi: không có mặt đất rõ, **không có bóng đổ**, nền phẳng, ánh sáng không có hướng |
| 1 (sau khi sửa) | 6/10 | 5 lỗi → còn 1: bóng đổ cứng, chưa mềm |
| 2 (sau khi sửa) | 7/10 | 1 lỗi: bóng đổ cứng thay vì mềm |

Chi phí cả 3 vòng: **$0.0072**.

---

## 6. Một bug thật, và cách tìm ra nó

Scene sakura sinh ra **cụm hoa anh đào đen kịt** (nhìn thấy rõ trong ảnh). Nguyên nhân:

```js
const blossomMaterial = new THREE.MeshStandardMaterial({
  color: 0xffffff, roughness: 0.9, side: THREE.DoubleSide,
  vertexColors: true          // ← geometry KHÔNG hề có attribute 'color'
});
```

Khi bật `vertexColors: true` mà hình học không có attribute `color`, Three.js lấy giá trị mặc định
`(0,0,0)` → mọi điểm ảnh bị nhân với 0 → **đen**. Màu hồng mà AI gán bằng `setColorAt()` cũng bị nhân
với 0 nên vô tác dụng.

**Fix 1 dòng** — bỏ hẳn dòng `vertexColors: true`. Đã render lại và xác minh bằng mắt: hoa ra hồng.

**Bài học:** *"0 lỗi console" không có nghĩa là "scene đẹp"*. Code chạy ngon vẫn có thể render sai màu.
Phải **chụp ảnh và nhìn** — đó chính là lý do vòng repair sinh ra.

---

## 7. Giới hạn thật (đã gặp, không phải lý thuyết)

- **Có thể quá tối.** Scene "neon alley" từng bị tối gần như đen dù đèn neon bật → mô tả thêm
  "bright", "well lit", "daylight". (Cổng chất lượng tự động giờ bắt được trường hợp này.)
- **Chữ CJK (Nhật/Trung) hiện thành ô vuông** trên máy render — do máy không có font CJK, **không phải
  lỗi HTML**. Trên máy anh sẽ hiện bình thường.
- **Không có vật lý.** Rèo không đổ, nước không chảy, vật không rơi. Đây là cảnh tĩnh, phong cách
  "low-poly cinematic".
- **Không dùng được cho 3D print / PBR production.** Muốn mesh có topology thật, UV map, texture 4K →
  phải quay về pipeline 3D cũ (Blender / Hunyuan3D / TRELLIS).
- **Ảnh tham chiếu**: model đọc được ảnh, nhưng phải chỉ rõ phong cách ("in low-poly voxels"), nếu không
  nó sẽ tự diễn giải.

---

## 8. Chi phí thật

Giá API: input $0.15 / output $0.60 / cache-read $0.015 trên 1 triệu token.

| | One-shot | Repair loop (3 vòng) |
|---|---|---|
| Token | ~13k output | ~45k output |
| Chi phí | **~$0.005** | **~$0.02** |
| Thời gian | 30–160s | 5–15 phút |

Một scene 3D có ánh sáng, bóng đổ, camera xoay — **giá bằng 1 ly cà phê**.

---

## 9. Khi nào nên dùng, khi nào không

**Dùng tốt:**
- Mockup concept chưa cần art chất lượng cao
- Hero background / banner cho landing page, demo sản phẩm
- Khung cảnh cho video explainer
- Prototype game, prototype công nghiệp
- Test ý tưởng trước khi thuê người làm 3D

**Không dùng:**
- Asset production cần PBR / texture 4K / topology chuẩn
- 3D print (cần STL manifold)
- Cần chạy 60fps trên mobile cấu hình thấp
- Cần chính xác về kích thước vật lý / kỹ thuật

---

## 10. Vài lưu ý kỹ thuật

- **Móc sai lớn nhất của API MiniMax**: `thinking.budget_tokens` bị **bỏ qua âm thầm**. Phải dùng
  `output_config.effort` (low…max, mặc định `max`). Nếu không, model suy nghĩ hết ngân sách token →
  trả về nội dung rỗng. Em đã mất 1 lượt chạy 3 scene để phát hiện.
- `max_tokens` **tính cả token suy nghĩ**. Dùng 32768.
- Script gọi API lấy key từ `~/.nanobot/config.json` lúc chạy — key không bao giờ nằm trong lệnh hay
  lịch sử shell.
- **Ba loại canvas** phải nhận ra khi kiểm tra file: thẻ `<canvas>`, `createElement('canvas')`, và
  `new THREE.WebGLRenderer()` (renderer tự tạo canvas rồi append `renderer.domElement`). Bỏ sót
  loại thứ ba thì tool sẽ loại nhầm các scene hoàn toàn hợp lệ — lỗi này đã xảy ra và được sửa.

Skill đầy đủ: `~/workspace/skills/minimax-api-quirks/SKILL.md`
