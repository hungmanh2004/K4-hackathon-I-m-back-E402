# Design — VLearn AI Study Agent

**Ngày:** 2026-07-30
**Trạng thái:** đã chốt với người dùng, sẵn sàng chuyển sang implementation plan

> **Thay thế `implementation_plan.md`.** Bản plan cũ mô tả kiến trúc pipeline với 4 endpoint riêng (`/api/summarize`, `/api/mindmap`, `/api/audio`, `/api/chat`). Thiết kế này gộp lại thành **một** endpoint `/api/agent` và biến ba tính năng đó thành tool bên trong một agent loop. Khi build, bám theo file này.

## Mục tiêu

Một AI Agent chạy local, đọc một file slide PDF cố định và tạo ra ba dạng đầu ra:

1. **Tóm tắt** — text ngắn có dẫn trang
2. **Mind map** — sơ đồ tư duy render được, mỗi node lá neo vào trang gốc
3. **Audio** — podcast ~1 phút nghe được ngay trong trình duyệt

Demo gói gọn trong project local: một backend Python + một file HTML mở thẳng bằng browser. **Không deploy, không database, không authentication.**

## Quyết định đã chốt

| Quyết định | Chọn | Lý do |
|---|---|---|
| Phạm vi | Cả 3 tính năng | Mục tiêu là trình diễn khả năng agent, chấp nhận đánh đổi độ sâu |
| Kích hoạt | Hybrid: 3 nút + chat, cùng một agent loop | Nút = đường lui an toàn khi demo live; chat = chỗ khoe agent chain tool |
| Input | PDF cố định `HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf` | Ít code nhất, chạy chắc nhất |
| Audio | Script 300-500 từ từ summary → 1 lần gọi TTS | Vừa đủ phát trọn trong demo 5 phút, không phụ thuộc mind map |
| LLM | OpenAI `gpt-4o-mini` | Người dùng chỉ định |
| TTS | **ElevenLabs** (`eleven_turbo_v2_5`) | Giọng tiếng Việt tự nhiên hơn hẳn OpenAI `tts-1` |
| Trace | Stream SSE, hiện từng bước live | Đây là bằng chứng trực quan "agent thật", không phải pipeline |
| Eval | Có, tối thiểu, chỉ kiểm thứ máy tự kiểm được | Rẻ, và là bảo hiểm cho phần chấm điểm |

## Kiến trúc

### Nguyên tắc cốt lõi: tool là cổng dữ liệu, agent tự nghĩ

Đây là điểm phân biệt agent thật với pipeline có UI.

**Cách sai** — tool tên là `summarize()`, bên trong tool lại gọi LLM. Agent chỉ làm nhiệm vụ định tuyến, LLM lồng LLM, chậm, và bản thân agent không đưa ra phán đoán nào.

**Cách đúng** — tool chỉ cấp quyền truy cập dữ liệu và kênh xuất kết quả. Toàn bộ phần suy nghĩ (đọc trang nào, khái niệm nào là nhánh chính, đã đủ thông tin chưa) nằm trong agent.

### Bộ tool

| Tool | Tham số | Trả về | Vai trò |
|---|---|---|---|
| `list_pages` | — | `[{page, first_line, char_count}]` | Mục lục rẻ tiền để agent khảo sát |
| `read_pages` | `pages: int[]` | text đầy đủ các trang đó | Đọc sâu chỗ agent thấy cần |
| `emit_summary` | `markdown: str` | ack | Đẩy kết quả ra tab Tóm tắt |
| `emit_mindmap` | `outline_md: str` | ack | Đẩy kết quả ra tab Mind Map |
| `render_audio` | `script: str` | `{url, char_count}` | Gọi ElevenLabs TTS, đẩy ra tab Audio |

`render_audio` **không** nhận tham số giọng. Giọng là cấu hình hệ thống (`ELEVENLABS_VOICE_ID` trong `.env`), không phải quyết định của agent — để agent chọn giọng chỉ tạo thêm chỗ sai mà không thêm giá trị nào.

Agent tự quyết trình tự: khảo sát mục lục → chọn trang đáng đọc → đọc → thấy thiếu thì đọc thêm → mới emit. Vòng lặp có phán đoán, và mỗi bước đều có thể sai.

Việc chain tool là điều pipeline không làm được: câu *"tóm tắt rồi vẽ sơ đồ luôn"* khiến agent gọi `read_pages` **một lần**, rồi `emit_summary` và `emit_mindmap` — không đọc lại PDF hai lượt.

### Luồng chạy

```
   [📝][🧠][🎧]  ─┐
   nút bơm prompt │
   cố định        ├──► POST /api/agent {message}   (SSE stream trả về)
   chat tự do   ──┘         │
                            ▼
        ┌───────────────────────────────────────────┐
        │  AGENT LOOP  (gpt-4o-mini, tool-calling)  │
        │  max 8 vòng — chặn loop vô hạn & đốt tiền │
        │                                           │
        │   ① list_pages()      "deck có gì?"       │
        │   ② read_pages([...]) "đọc chỗ cần"       │
        │   ③ đủ chưa? ──chưa──► quay lại ②         │
        │   ④ emit_* / render_audio                 │
        │                                           │
        │   mỗi bước → yield 1 event ra SSE         │
        └──────────────┬────────────────────────────┘
                       ▼
        ┌───────────────────────────────────────────┐
        │  GUARD (code thuần, không LLM)            │
        │  • số trang trong [Tr.N] có tồn tại?      │
        │  • outline có ≥2 cấp, ≤4 depth?           │
        │  • script ≤5000 ký tự? (giới hạn TTS)     │
        └──────┬─────────────────────┬──────────────┘
          pass │                     │ fail
               ▼                     ▼
     tab tương ứng render    node/mục gắn cờ ⚠
     + panel trace hiện      "không tìm thấy căn cứ"
       từng bước live        user tự xoá/giữ
```

Text PDF được extract **một lần lúc server khởi động** và cache trong RAM. File cố định nên không cần parse lại mỗi request.

### Backend — `codebase/`

Mỗi file một trách nhiệm, đủ nhỏ để đọc hết trong một lượt:

| File | Trách nhiệm | Phụ thuộc |
|---|---|---|
| `pdf_parser.py` | PDF → text theo trang. Hàm thuần, **không AI**. | pymupdf |
| `tools.py` | Cài đặt 5 tool + JSON schema khai báo cho OpenAI | pdf_parser, tts |
| `agent.py` | Vòng lặp tool-calling, sinh event, chặn ở 8 vòng | openai, tools |
| `tts.py` | Bọc ElevenLabs TTS → file mp3 trong `audio_output/`, kèm cache | elevenlabs |
| `server.py` | Tầng HTTP mỏng: `/api/agent`, `/audio/{f}`, `/health` | agent |

Chỉ **một** endpoint làm việc thật (`/api/agent`), vì nút và chat đi chung một đường. Không còn `/api/summarize`, `/api/mindmap`, `/api/audio` riêng — ba thứ đó đã thành tool bên trong agent.

### Frontend — `vlearn_clone.html`

Giữ nguyên layout hiện có (366 dòng, đang là mock). Thêm vào sidebar chatbot:

- **Hàng 3 nút** `📝 Tóm tắt · 🧠 Mind Map · 🎧 Audio` — mỗi nút bơm một câu tiếng Việt cố định vào cùng `/api/agent`
- **Output panel 3 tab** bên dưới khung chat
- **Panel "Agent đang làm gì"** — thu gọn được, hiện trace từng bước theo thời gian thực
- **CDN:** `markmap-autoloader` (render mind map từ markdown heading) + `marked.js` (render summary)
- Thay `sendMessage()` mock hiện tại bằng `fetch()` đọc SSE stream

**Vì sao markmap chứ không mermaid/d3/mind-elixir:** cú pháp `mindmap` của mermaid nhạy cảm với thụt lề, LLM phá syntax thường xuyên, và khi hỏng thì hỏng trắng màn hình. Markdown heading outline chịu lỗi tốt hơn — sai chút vẫn render, không render được thì vẫn đọc được như text thường. Với demo live, degrade gracefully đáng giá hơn đẹp hơn 10%.

---

## Ghi chú chi tiết — SSE hoạt động thế nào

Phần này viết kỹ vì người dùng cần giải thích được cơ chế, không chỉ chạy được.

### SSE là gì

Server-Sent Events là stream **một chiều** server → client, chạy trên HTTP thường. Không phải WebSocket (WebSocket hai chiều, phức tạp hơn nhiều). Toàn bộ giao thức chỉ gồm:

- Response header `Content-Type: text/event-stream`
- Mỗi sự kiện là một dòng `data: <nội dung>` kết thúc bằng **hai** ký tự xuống dòng `\n\n`

Hai xuống dòng chính là dấu phân cách bản ghi. Đó là hết. Không có handshake, không có framing nhị phân.

```
data: {"type":"tool_call","name":"list_pages"}

data: {"type":"tool_result","name":"list_pages","summary":"29 trang"}

data: {"type":"done"}

```

### Vì sao không dùng `EventSource`

Trình duyệt có sẵn API `EventSource` cho SSE, nhưng **`EventSource` chỉ gửi được GET, không gửi được body**. Ta cần POST kèm câu hỏi của người dùng, nên phải tự đọc stream bằng `fetch()` + `ReadableStream`.

Đây là chi tiết dễ mất thời gian nhất nếu không biết trước.

### Phía server — generator sinh event

`agent.py` phơi ra một generator. Mỗi lần agent làm xong một bước thì `yield` một dict:

```python
def run_stream(message: str):
    """Chạy agent, yield từng event một. Đây là nguồn sự thật duy nhất."""
    yield {"type": "status", "text": "Đang khởi động agent..."}

    messages = [system_prompt, {"role": "user", "content": message}]

    for iteration in range(MAX_ITERATIONS):        # MAX_ITERATIONS = 8
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOL_SCHEMAS,
        )
        choice = response.choices[0]

        if not choice.message.tool_calls:           # agent trả lời text → xong
            yield {"type": "message", "content": choice.message.content}
            break

        messages.append(choice.message)

        for call in choice.message.tool_calls:
            yield {"type": "tool_call", "name": call.function.name,
                   "args": call.function.arguments}

            result = execute_tool(call)             # tools.py làm việc thật

            yield {"type": "tool_result", "name": call.function.name,
                   "summary": result.short_description}

            if result.artifact:                     # emit_* / render_audio
                yield {"type": "artifact", **result.artifact}

            messages.append(tool_result_message(call, result))
    else:
        yield {"type": "status", "text": "Đã chạm giới hạn 8 vòng, trả kết quả hiện có."}

    yield {"type": "done"}
```

`server.py` bọc generator đó thành SSE — chỉ là việc gói mỗi dict thành `data: ...\n\n`:

```python
from fastapi.responses import StreamingResponse
import json

@app.post("/api/agent")
def api_agent(req: AgentRequest):
    def event_stream():
        try:
            for event in agent.run_stream(req.message):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','message':str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

`ensure_ascii=False` là bắt buộc — không có nó tiếng Việt bị escape thành `\uXXXX`, vẫn chạy nhưng debug rất khó chịu.

Khối `try/except` bọc toàn bộ vòng lặp là quan trọng: nếu OpenAI lỗi giữa chừng mà không bắt, stream đứt im lặng và frontend treo mãi ở trạng thái loading. Bắt rồi đẩy event `error` thì UI biết đường hiển thị.

**Về generator đồng bộ:** `event_stream` ở đây là `def` thường, không phải `async def`. Starlette tự chạy generator đồng bộ trong threadpool nên không chặn event loop. Với demo local thì cách này đơn giản hơn và không có nhược điểm đáng kể.

### Phía client — đọc stream bằng fetch

```javascript
async function askAgent(message) {
  const res = await fetch('http://localhost:8000/api/agent', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message}),
  });

  const reader  = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const {done, value} = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, {stream: true});

    // Chunk mạng KHÔNG trùng ranh giới event. Một event có thể bị cắt
    // làm đôi giữa hai chunk, hoặc hai event về chung một chunk.
    // Nên phải giữ buffer và chỉ lấy phần đã trọn vẹn (kết thúc bằng \n\n).
    const parts = buffer.split('\n\n');
    buffer = parts.pop();                  // phần cuối có thể còn dở → giữ lại

    for (const part of parts) {
      if (!part.startsWith('data: ')) continue;
      handleEvent(JSON.parse(part.slice(6)));
    }
  }
}
```

Chỗ dễ sai nhất là **buffering**. Chunk do mạng trả về không trùng ranh giới event: một event có thể bị cắt làm đôi, hoặc ba event về chung một chunk. Nếu `JSON.parse` thẳng từng chunk sẽ vỡ ngẫu nhiên và rất khó lần ra. Cách xử lý: tích luỹ vào `buffer`, tách theo `\n\n`, và luôn giữ lại phần tử cuối (có thể còn dở) cho vòng sau.

`decoder.decode(value, {stream: true})` cũng cần cờ `stream: true` vì lý do tương tự ở tầng ký tự — một ký tự tiếng Việt nhiều byte có thể bị cắt giữa hai chunk.

### Bảng sự kiện

`handleEvent` phân nhánh theo `type`:

| `type` | Trường kèm theo | UI làm gì |
|---|---|---|
| `status` | `text` | Thêm dòng vào panel trace |
| `tool_call` | `name`, `args` | Thêm dòng trace: `📄 đọc trang 3-11` |
| `tool_result` | `name`, `summary` | Cập nhật dòng trace vừa rồi thành ✓ |
| `artifact` | `kind` (`summary`/`mindmap`/`audio`), `content` hoặc `url` | Render vào tab tương ứng, tự chuyển sang tab đó |
| `message` | `content` | Hiện như tin nhắn bot trong khung chat |
| `error` | `message` | Hiện lỗi đỏ, tắt trạng thái loading |
| `done` | — | Tắt loading, đóng stream |

Giữ bảng này ổn định là đủ để backend và frontend phát triển độc lập.

---

## Ghi chú chi tiết — ElevenLabs TTS

### Chọn model: đây là chỗ dễ mất một giờ

ElevenLabs có nhiều model và **không phải model nào cũng hỗ trợ tiếng Việt**:

| Model | Ngôn ngữ | Tiếng Việt? |
|---|---|---|
| `eleven_multilingual_v2` | 29 thứ tiếng | **Không có trong danh sách** |
| `eleven_turbo_v2_5` | 32 thứ tiếng | Có |
| `eleven_flash_v2_5` | 32 thứ tiếng | Có, nhanh nhất, chất lượng thấp hơn chút |

Trực giác sẽ dẫn bạn tới `eleven_multilingual_v2` vì tên nó có chữ "multilingual" và nó được quảng cáo là model chất lượng cao nhất — nhưng tiếng Việt được thêm vào ở nhóm 32 thứ tiếng, tức `turbo_v2_5` / `flash_v2_5`.

**Chốt: `eleven_turbo_v2_5`.** Nếu ElevenLabs đã có model mới hơn phủ tiếng Việt tốt hơn (dòng `v3`), thử luôn trong task test đầu tiên — nhưng mặc định lấy `turbo_v2_5` vì nó chắc chắn có tiếng Việt.

Giọng: chọn một `voice_id` từ thư viện, ghi vào `.env`. Chất lượng accent tiếng Việt **khác nhau đáng kể giữa các giọng** kể cả khi cùng model — nên task test đầu tiên phải nghe thử 2-3 giọng rồi mới chốt, đừng lấy giọng đầu tiên tìm thấy.

### Hạn mức: rủi ro thật, không phải cảnh báo cho có

Free tier ElevenLabs cấp khoảng **10.000 credit/tháng**, tiêu xấp xỉ 1 credit mỗi ký tự.

Một script podcast 300-500 từ tiếng Việt ≈ **2.000-3.000 ký tự**. Tức free tier chỉ đủ khoảng **3-5 lần sinh audio cho cả tháng**.

Trong một ngày build, bạn sẽ gọi TTS nhiều hơn 5 lần — chỉ riêng việc thử giọng đã hết. Vì vậy thiết kế bắt buộc có hai lớp chặn:

**1. Cache theo nội dung script.** `tts.py` băm script (SHA-256), lấy 16 ký tự đầu làm tên file. Script y hệt → trả lại file cũ, không gọi API.

```python
def generate_audio(script: str) -> str:
    key = hashlib.sha256(script.encode()).hexdigest()[:16]
    path = AUDIO_DIR / f"{key}.mp3"
    if path.exists():
        return path.name          # cache hit — không tốn credit
    ...                           # gọi ElevenLabs, ghi file
    return path.name
```

Chạy lại cùng một demo không tốn thêm credit. Đây cũng là lưới an toàn khi demo live: nếu đã chạy thử trước đó, lần demo thật là cache hit, không phụ thuộc mạng và không thể hết quota giữa chừng.

**2. Test bằng câu ngắn.** Khi thử giọng, dùng 1-2 câu (~100 ký tự), không dùng script đầy đủ. Thử 3 giọng hết ~300 credit thay vì ~9.000.

### Hai key, kiểm tra ngay lúc khởi động

Giờ cần **cả hai**: `OPENAI_API_KEY` (LLM) và `ELEVENLABS_API_KEY` (TTS). Server kiểm cả hai lúc start và từ chối chạy nếu thiếu, kèm thông báo nói rõ thiếu key nào.

Lý do làm chặt: thiếu key OpenAI thì hỏng ngay từ lần bấm đầu tiên nên phát hiện được liền — nhưng thiếu key ElevenLabs thì summary và mind map vẫn chạy ngon, chỉ tới lúc bấm 🎧 mới vỡ. Trong demo live, đó là kiểu lỗi tệ nhất.

### Khác biệt so với OpenAI TTS

| | OpenAI `tts-1` | ElevenLabs `turbo_v2_5` |
|---|---|---|
| Giới hạn/lần gọi | 4.096 ký tự | ~5.000 ký tự (rộng hơn nhu cầu) |
| Giọng | tên có sẵn (`nova`...) | `voice_id` từ thư viện |
| Trả về | object có `stream_to_file()` | generator các chunk bytes → tự ghi file |
| Chi phí | trả theo dùng, không quota cứng | free tier có quota tháng, **hết là dừng** |

Điểm cần chú ý khi code: ElevenLabs trả **generator các chunk bytes**, không có sẵn `stream_to_file()` như OpenAI. Phải tự gom:

```python
audio = client.text_to_speech.convert(
    voice_id=VOICE_ID, model_id="eleven_turbo_v2_5",
    text=script, output_format="mp3_44100_128",
)
with open(path, "wb") as f:
    for chunk in audio:
        f.write(chunk)
```

Giới hạn ký tự rộng hơn OpenAI nên với script ~3.000 ký tự thì **không cần cắt**. Guard vẫn giữ phép kiểm độ dài, nhưng ngưỡng nâng lên 5.000 và trên thực tế sẽ không chạm tới.

## Ghi chú chi tiết — eval tối thiểu

### Nguyên tắc

Chỉ kiểm **những thứ máy tự kiểm được**, không cần người chấm tay. Mục tiêu không phải đo "chất lượng tóm tắt hay dở" (việc đó cần người), mà bắt các lỗi cấu trúc và lỗi bịa nguồn — vốn là loại lỗi im lặng và nguy hiểm nhất.

### Một điểm vào duy nhất cho cả stream lẫn eval

Eval không cần stream. Nhưng **không** viết một đường chạy thứ hai cho nó — hai đường chạy sẽ trôi khỏi nhau và eval sẽ đo một thứ khác với thứ đang chạy thật.

Cách làm: `run()` chỉ là `run_stream()` đã được rút cạn.

```python
def run(message: str) -> dict:
    """Bản đồng bộ của run_stream — dùng cho eval. Cùng một logic."""
    trace, artifacts, error = [], {}, None
    for event in run_stream(message):
        trace.append(event)
        if event["type"] == "artifact":
            artifacts[event["kind"]] = event
        elif event["type"] == "error":
            error = event["message"]
    return {"trace": trace, "artifacts": artifacts, "error": error}
```

Một cài đặt, hai cách dùng.

### `eval/golden_set.json`

Mỗi case gồm câu hỏi đầu vào và danh sách phép kiểm cần thoả:

```json
[
  {
    "id": "S01",
    "message": "Tóm tắt slide này giúp tôi",
    "checks": ["no_error", "summary_nonempty", "summary_has_citation",
               "within_iteration_limit"]
  },
  {
    "id": "M01",
    "message": "Vẽ sơ đồ tư duy cho toàn bộ slide",
    "checks": ["no_error", "mindmap_pages_valid", "mindmap_min_branches_3",
               "mindmap_max_depth_4", "within_iteration_limit"]
  },
  {
    "id": "C01",
    "message": "Tóm tắt rồi vẽ sơ đồ luôn",
    "checks": ["no_error", "summary_nonempty", "mindmap_pages_valid",
               "single_read_pass"]
  }
]
```

Khoảng 10 case, phủ: 3 tính năng đơn lẻ, 2-3 case chain tool, 2 case biên (hỏi thứ không có trong slide, hỏi trang vượt số trang thật).

### Eval không được đốt quota TTS

Đây là ràng buộc bắt buộc, không phải tối ưu. Free tier ElevenLabs chỉ đủ ~3-5 lần sinh audio mỗi tháng — chạy trọn bộ eval 10 case mà mỗi case gọi TTS thật là hết sạch quota trong một lượt.

Hai biện pháp:

1. **Đúng một case duy nhất** trong golden set chạm tới audio. Chín case còn lại chỉ hỏi summary/mind map.
2. `run_eval.py` mặc định chạy với `TTS_MODE=stub` — `render_audio` trả về đường dẫn giả và số ký tự thật, **không gọi API**. Vẫn kiểm được agent có gọi tool đúng lúc, đúng thứ tự, script đúng độ dài. Muốn nghe thật thì chạy `TTS_MODE=real python eval/run_eval.py`.

Phân biệt cho rõ: eval ở đây kiểm **agent có điều phối đúng không**, không kiểm giọng đọc hay dở. Giọng phải nghe bằng tai, và việc đó làm một lần lúc chốt giọng — không nhét vào vòng lặp tự động.

### Các phép kiểm

| Tên | Kiểm gì | Vì sao quan trọng |
|---|---|---|
| `no_error` | Không có event `error` | Chạy trót lọt |
| `summary_nonempty` | Summary ≥100 ký tự | Bắt trường hợp emit rỗng |
| `summary_has_citation` | Có ít nhất một `[Tr.N]` | Buộc grounding vào tài liệu |
| `mindmap_pages_valid` | **Mọi** `[Tr.N]` đều thoả `1 ≤ N ≤ page_count` | Bắt bịa số trang — lỗi im lặng nguy hiểm nhất |
| `mindmap_min_branches_3` | ≥3 nhánh cấp 1 | Bắt outline suy biến thành danh sách phẳng |
| `mindmap_max_depth_4` | Không quá 4 cấp heading | Bắt cây quá sâu, không đọc được |
| `within_iteration_limit` | Không chạm trần 8 vòng | Bắt agent loanh quanh không hội tụ |
| `single_read_pass` | Chỉ gọi `read_pages` một lần | Chứng minh chain tool đúng cách, không đọc lại PDF |

`mindmap_pages_valid` là phép kiểm giá trị nhất: nó bắt đúng loại lỗi mà mắt người bỏ sót — mind map trông rất hợp lý nhưng trỏ sang trang không tồn tại.

### `eval/run_eval.py`

Chạy `python eval/run_eval.py`:

1. Nạp golden set
2. Với mỗi case: gọi `agent.run(message)`
3. Áp từng phép kiểm lên kết quả
4. In bảng pass/fail ra terminal
5. Ghi `eval/results-<timestamp>.md` — bảng đầy đủ, **gồm cả case trượt**

Ghi lại cả case trượt là có chủ ý. Một bảng toàn ✓ không nói lên điều gì; bảng có ✗ kèm lý do mới cho biết hệ thống hỏng ở đâu.

---

## Rủi ro và cách xử

| Rủi ro | Xử lý |
|---|---|
| Thiếu `OPENAI_API_KEY` **hoặc** `ELEVENLABS_API_KEY` | Server **từ chối khởi động**, nói rõ thiếu key nào. Thiếu key ElevenLabs đặc biệt hiểm vì summary/mind map vẫn chạy ngon, chỉ vỡ lúc bấm 🎧 giữa demo |
| **Hết quota ElevenLabs giữa demo** | Cache theo hash script — chạy thử trước demo thì lúc demo là cache hit, không gọi API. Eval mặc định `TTS_MODE=stub`. Thử giọng bằng câu ngắn ~100 ký tự |
| Chọn nhầm model không có tiếng Việt | Chốt `eleven_turbo_v2_5`. `eleven_multilingual_v2` **không** có tiếng Việt dù tên gọi gợi ý ngược lại |
| Giọng đọc tiếng Việt nghe kỳ | Chất lượng accent khác nhau đáng kể giữa các `voice_id` cùng model. **Task đầu tiên: nghe thử 2-3 giọng bằng câu ngắn rồi mới chốt** |
| Agent lặp vô hạn | Cứng 8 vòng, hết thì trả kết quả tốt nhất đang có + báo qua event `status` |
| Script vượt 5000 ký tự | Cắt ở **ranh giới câu** + báo rõ đã cắt — không cắt giữa từ, không im lặng. Thực tế script ~3.000 ký tự nên hiếm khi chạm |
| markmap render lỗi | Fallback hiện outline markdown thô |
| OpenAI/ElevenLabs lỗi giữa stream | `try/except` bọc generator, đẩy event `error`, UI tắt loading |
| Stream đứt, frontend treo loading | Event `done` luôn được yield ở cuối; client cũng tắt loading khi `reader` báo hết |

Hai rủi ro nhóm TTS (chọn sai model, hết quota) là thứ duy nhất có thể giết hẳn một chân sản phẩm, nên task đầu tiên trong plan phải là **test giọng tiếng Việt bằng câu ngắn** trước khi build bất cứ thứ gì khác.

## Ngoài phạm vi

Ghi rõ để không trôi scope:

- Không upload file — PDF cố định
- Không deploy, không database, không authentication
- Không đa người dùng, không lưu lịch sử hội thoại qua các lần chạy
- Không podcast toàn bộ deck — chỉ ~1 phút từ summary
- Không nghe theo nhánh mind map (đã cân nhắc và loại: buộc audio phụ thuộc mind map hoàn thành trước)
- Không chấm chất lượng nội dung bằng máy — eval chỉ kiểm cấu trúc và tính hợp lệ của trích dẫn trang

## Cấu trúc file sau khi build

```
K4-hackathon-I-m-back-E402/
├── vlearn_clone.html              ← frontend, mở thẳng bằng browser
├── HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf
├── codebase/
│   ├── requirements.txt           ← đã có, cần THÊM `elevenlabs`
│   ├── .env.example               ← OPENAI_API_KEY, ELEVENLABS_API_KEY,
│   │                                 ELEVENLABS_VOICE_ID
│   ├── .gitignore                 ← .env, __pycache__, audio_output/*.mp3
│   ├── pdf_parser.py
│   ├── tools.py
│   ├── agent.py
│   ├── tts.py
│   ├── server.py
│   └── audio_output/
└── eval/
    ├── golden_set.json
    ├── run_eval.py
    └── results-<timestamp>.md     ← sinh ra khi chạy
```

## Cách chạy

```bash
cd codebase
pip install -r requirements.txt
cp .env.example .env        # điền OPENAI_API_KEY + ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID
uvicorn server:app --reload --port 8000
```

Rồi mở `vlearn_clone.html` bằng browser.

Chạy eval:

```bash
python eval/run_eval.py                    # mặc định TTS_MODE=stub, không tốn credit
TTS_MODE=real python eval/run_eval.py      # gọi ElevenLabs thật — chỉ chạy khi cần
```
