import os
import soundcard as sc
import soundfile as sf
import numpy as np
import threading
import queue
import time

# 音声データを保存するディレクトリ
OUTPUT_DIR = "wav_files"


# 音声データが無音かどうかを判定する関数
def is_silent(data, threshold=0.01, sample_rate=48000):
    sample_size = int(sample_rate * 0.1)  # 0.1秒ごとのデータのみを検査
    return np.abs(data[:sample_size]).mean() < threshold


# 音声データをファイルに保存する関数
def save_audio(frames, samplerate, output_file_name):
    # 音声データを結合
    audio_data = np.concatenate(frames)

    # 音声データが無音の場合は保存しない
    if is_silent(audio_data):
        return

    # 音声データを指定ディレクトリに保存
    output_file_path = os.path.join(OUTPUT_DIR, output_file_name)
    sf.write(output_file_path, audio_data, samplerate)
    print(f"[OPPY-SOUND-RECORDER] File Saved: {output_file_name}", flush=True)


# 無音を検出して録音を継続しつつファイルに出力する関数
def record_and_save_on_conditions(
        output_file_prefix,  # 出力ファイルのプレフィックス(ファイル名の先頭部分)
        samplerate,  # サンプリング周波数
        silence_duration,  # 無音と判定する時間(秒)
        max_record_duration,  # 最大録音時間(秒)
        check_interval # 録音データを取得する間隔(秒)
):
    mic = sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True)
    frames = []
    silent_frames = 0
    file_count = 0
    audio_queue = queue.Queue()
    stop_event = threading.Event()
    last_save_time = time.time()

    # 音声データをファイルに保存するスレッド
    def audio_writer():
        try:
            while True:
                frames, output_file_name = audio_queue.get()
                if frames is None:
                    break
                save_audio(frames, samplerate, output_file_name)
        except Exception as e:
            print(f"[OPPY-SOUND-RECORDER] Audio Writer Error: {e}", flush=True)

    # ユーザー入力を受け付けるスレッド
    def input_listener():
        try:
            while True:
                # ユーザー入力を受け付ける
                user_input = input()

                # "exit"と入力されたら録音を停止
                if user_input.strip().lower() == "exit":
                    stop_event.set()
                    break
        except Exception as e:
            print(f"[OPPY-SOUND-RECORDER] Input Listener Error: {e}", flush=True)

    # スレッドの開始
    writer_thread = threading.Thread(target=audio_writer)
    input_thread = threading.Thread(target=input_listener)
    writer_thread.start()
    input_thread.start()

    # 録音開始
    try:
        with mic.recorder(samplerate=samplerate) as recorder:
            print("[OPPY-SOUND-RECORDER] Recording started.", flush=True)
            while not stop_event.is_set():
                # 録音データを取得
                data = recorder.record(numframes=int(samplerate * check_interval))
                frames.append(data)

                # 無音かどうかを判定
                if is_silent(data, sample_rate=samplerate):
                    silent_frames += 1
                else:
                    silent_frames = 0

                # 最後にファイルに保存した時間からの経過時間(秒)を計算
                current_time = time.time()
                elapsed_time_since_last_save = current_time - last_save_time

                # 無音が指定秒数続くか、指定秒数以上録音した場合
                if silent_frames >= silence_duration / check_interval or elapsed_time_since_last_save >= max_record_duration:
                    # ファイルに保存
                    if frames:
                        output_file_name = f"{output_file_prefix}_{file_count}.wav"
                        audio_queue.put((frames, output_file_name))
                        frames = []
                        file_count += 1
                        silent_frames = 0
                        last_save_time = current_time

        # 終了時に残っているデータを保存
        if frames:
            output_file_name = f"{output_file_prefix}_{file_count}.wav"
            audio_queue.put((frames, output_file_name))
    except Exception as e:
        print(f"[OPPY-SOUND-RECORDER] Recording Error: {e}", flush=True)
    finally:
        # 録音の終了シグナル
        audio_queue.put((None, None))

        # スレッドの終了
        writer_thread.join()
        input_thread.join()
        print("[OPPY-SOUND-RECORDER] Recording stopped.", flush=True)


# main関数
if __name__ == "__main__":
    # 引数を取得してパース
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default="output", help="Output file prefix")
    parser.add_argument("--samplerate", type=int, default=48000, help="Sampling rate")
    parser.add_argument("--silence_duration", type=float, default=3, help="Silence duration (seconds)")
    parser.add_argument("--max_record_duration", type=float, default=10, help="Max record duration (seconds)")
    parser.add_argument("--check_interval", type=float, default=0.1, help="Check interval (seconds)")
    parser.add_argument("--output_dir", type=str, default="wav_files", help="Output directory")
    args = parser.parse_args()

    # 音声データを保存するディレクトリを設定
    OUTPUT_DIR = args.output_dir

    # 音声データを保存するディレクトリが存在しない場合は作成
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 録音を開始
    record_and_save_on_conditions(
        "output",
        samplerate=args.samplerate,  # サンプリング周波数
        silence_duration=args.silence_duration,  # 無音と判定する時間(秒)
        max_record_duration=args.max_record_duration,  # 最大録音時間(秒)
        check_interval=args.check_interval  # 録音データを取得する間隔(秒)
    )
