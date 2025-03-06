from pydub import AudioSegment

def convert_mp3_to_aac(mp3_file, output_file):
    # 加载mp3文件
    audio = AudioSegment.from_mp3(mp3_file)

    # 转换为单声道
    mono_audio = audio.set_channels(1)

    # 设置采样率为16000（或8000）
    sample_rate = 16000  # 或者8000
    mono_audio = mono_audio.set_frame_rate(sample_rate)

    # 设置比特率为48000（或其他推荐值）
    bitrate = "48k"  # CBR bitrates 24000-96000，推荐48000

    # 导出为AAC编码的M4A文件
    mono_audio.export(output_file, format="ipod", codec="aac", parameters=[
        "-b:a", bitrate,
        "-ar", str(sample_rate),
        "-ac", "1",
        "-profile:a", "aac_low",  # AAC-LC
        "-movflags", "+faststart",
        "-brand", "mp42"
    ])

# 示例调用
convert_mp3_to_aac("E:/data/WeChat Files/audio/262193221195193829.mp3", "E:/data/WeChat Files/audio/output.m4a")