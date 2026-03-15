# コマンド別シーケンス図

## 1. `mojiokoshi file` — 音声ファイルの文字起こし

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant CLI as cli.py<br>cmd_file
    participant WT as WhisperTranscriber
    participant Whisper as mlx-whisper
    participant FS as ファイルシステム

    User->>CLI: mojiokoshi file <input> [-o output]
    CLI->>FS: 入力ファイルの存在確認
    alt ファイルが存在しない
        CLI-->>User: エラー終了
    end
    CLI->>WT: WhisperTranscriber(model, language)
    CLI->>WT: transcribe(input_path)
    WT->>Whisper: mlx_whisper.transcribe()
    Whisper-->>WT: {text, segments, language}
    WT-->>CLI: TranscriptionResult
    CLI->>FS: 結果をテキストファイルに保存
    CLI-->>User: 結果表示 + 保存先パス
```

## 2. `mojiokoshi record` — 録音して文字起こし

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant CLI as cli.py<br>cmd_record
    participant Rec as MicrophoneRecorder
    participant SD as sounddevice
    participant WT as WhisperTranscriber
    participant FS as ファイルシステム

    User->>CLI: mojiokoshi record [-d duration] [--save-audio]

    alt duration指定あり
        CLI->>Rec: record_blocking(duration)
        Rec->>SD: sd.rec() + sd.wait()
        SD-->>Rec: 音声データ (float32)
        Rec-->>CLI: audio
    else duration未指定（手動停止）
        CLI->>Rec: start_recording()
        Rec->>SD: InputStream開始
        loop Ctrl+Cまで
            SD-->>Rec: コールバックで音声チャンク蓄積
        end
        User->>CLI: Ctrl+C
        CLI->>Rec: stop_recording()
        Rec-->>CLI: audio
    end

    alt --save-audio指定あり
        CLI->>Rec: save_wav(audio, wav_path)
        Rec->>FS: WAV保存
        CLI->>WT: transcribe(wav_path)
        Note right of CLI: 保存済みWAVを再利用
    else --save-audio未指定
        CLI->>Rec: save_wav(audio, temp_path)
        Rec->>FS: 一時WAV保存
        CLI->>WT: transcribe(temp_path)
        CLI->>FS: 一時ファイル削除（finally）
    end

    WT-->>CLI: TranscriptionResult
    CLI->>FS: 結果をテキストファイルに保存
    CLI-->>User: 結果表示 + 保存先パス
```

## 3. `mojiokoshi realtime` — リアルタイム文字起こし

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant CLI as cli.py<br>cmd_realtime
    participant RT as RealtimeTranscriber
    participant Rec as MicrophoneRecorder
    participant SD as sounddevice
    participant WT as WhisperTranscriber
    participant FS as ファイルシステム

    User->>CLI: mojiokoshi realtime [--threshold] [--silence]
    CLI->>RT: RealtimeTranscriber(model, language, ...)
    CLI->>RT: start()

    Note over RT: モデルウォームアップ（無音WAVで初回ロード）
    RT->>WT: transcribe(無音WAV)

    RT->>Rec: start_recording(on_chunk=_process_chunk)
    Rec->>SD: InputStream開始

    loop Ctrl+Cまで
        SD-->>Rec: 音声チャンク
        Rec-->>RT: _process_chunk(chunk)

        alt 音声あり（振幅 > threshold）
            Note over RT: バッファに蓄積
        else 発話中に無音が続いた
            Note over RT: 無音サンプル数を加算
            alt 無音がsilence_duration超過
                RT->>RT: _transcribe_buffer()
                Note over RT: バッファ取得（Lock内）
                RT->>RT: 別スレッドで文字起こし開始
                RT->>WT: transcribe(temp_wav)
                WT-->>RT: TranscriptionResult
                RT-->>CLI: on_text(text)コールバック
                CLI-->>User: >> テキスト表示
            end
        end
    end

    User->>CLI: Ctrl+C
    CLI->>RT: stop()
    RT->>Rec: stop_recording()
    RT->>RT: 残りバッファを文字起こし
    RT->>RT: 最後のスレッドのjoin待ち
    RT-->>CLI: 全テキスト
    CLI->>FS: テキストファイルに保存
    CLI-->>User: 保存先パス
```

## 4. `mojiokoshi devices` — デバイス一覧表示

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant CLI as cli.py<br>cmd_devices
    participant Rec as MicrophoneRecorder
    participant SD as sounddevice

    User->>CLI: mojiokoshi devices
    CLI->>Rec: list_devices()
    Rec->>SD: query_devices()
    SD-->>Rec: デバイス一覧
    Rec-->>CLI: 入力デバイスのリスト
    CLI-->>User: デバイスID・名前・デフォルト表示
```

## 5. `mojiokoshi-summarize` — 文字起こしテキストの校正・要約

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant Main as summarize.py<br>main
    participant Sum as summarize()
    participant Ollama as Ollama API
    participant FS as ファイルシステム

    User->>Main: mojiokoshi-summarize <input> [-m model] [-c correction-model]
    Main->>FS: 入力テキスト読み込み
    Main->>Sum: summarize(text, model, correction_model)

    Note over Sum: Stage 1: テキスト校正
    Sum->>Sum: split_into_chunks_with_context(text)
    loop 各チャンク
        Sum->>Sum: correct_chunk(context, main_text, model)
        Sum->>Ollama: POST /api/chat（校正プロンプト + CorrectedChunkスキーマ）
        Ollama-->>Sum: {corrected_text: "..."}
    end
    Note over Sum: 校正済みチャンクを結合

    Note over Sum: Stage 2: 議事録生成
    Sum->>Ollama: POST /api/chat（要約プロンプト + MeetingNotesスキーマ）
    Ollama-->>Sum: {summary, key_points, ...}
    Sum->>Sum: to_markdown(notes, corrected_text)
    Sum-->>Main: Markdown文字列

    Main->>FS: Markdownファイルに保存
    Main-->>User: 保存先パス
```
