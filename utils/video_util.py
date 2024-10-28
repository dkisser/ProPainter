import cv2
import os


# 视频分割
def split_video(input_path, output_dir, segment_duration):
    """

    Args:
        input_path: 原始视频路径
        output_dir: 输出目录
        segment_duration: 切分时长（s）

    Returns:

    """

    # 打开视频文件
    video = cv2.VideoCapture(input_path)

    # 获取视频的帧率和总帧数
    fps = video.get(cv2.CAP_PROP_FPS)
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

    # 计算每个片段的帧数
    segment_frames = int(segment_duration * fps)

    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 初始化输出视频写入器
    fourcc = cv2.VideoWriter.fourcc(*'mp4v')
    segment_count = 0
    out = None

    output_files = []
    for frame_number in range(total_frames):
        ret, frame = video.read()
        if not ret:
            break

        if frame_number % segment_frames == 0:
            if out is not None:
                out.release()
            output_path = os.path.join(output_dir, f'segment_{segment_count}.mp4')
            out = cv2.VideoWriter(output_path, fourcc, fps, (frame.shape[1], frame.shape[0]))
            segment_count += 1
            output_files.append(output_path)

        out.write(frame)

    if out is not None:
        out.release()

    video.release()
    return output_files


# 视频合并
def merge_videos(input_dir, output_path, scan_sub_dir:bool = False, regexp='.mp4'):
    """

    Args:
        scan_sub_dir: 是否合并子目录，true就是合并当前input_dir下的子目录, false就是合并当前input_dir目录
        input_dir: 要合并的视频目录
        output_path: 视频合并后的输出位置

    Returns:

    """
    # 获取所有视频片段
    video_files = get_subdir_mp4_files(input_dir, regexp) \
        if scan_sub_dir \
        else sorted([f for f in os.listdir(input_dir) if f.endswith(regexp)])
    if len(video_files) == 0:
        raise FileNotFoundError

    # 读取第一个视频片段以获取帧率和尺寸
    first_video_path = video_files[0]
    video = cv2.VideoCapture(first_video_path)
    fps = video.get(cv2.CAP_PROP_FPS)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video.release()

    # 初始化输出视频写入器
    fourcc = cv2.VideoWriter.fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # 逐个读取并写入视频片段
    for video_file in video_files:
        video = cv2.VideoCapture(video_file)

        while True:
            ret, frame = video.read()
            if not ret:
                break
            out.write(frame)

        video.release()

    out.release()


def get_subdir_mp4_files(input_dir, regexp='.mp4') -> []:
    mp4_files = []
    for root, dirs, files in os.walk(input_dir):
        for dir in dirs:
            sub_path = os.path.join(root, dir)
            for sub_root, sub_dirs, sub_files in os.walk(sub_path):
                for file in sub_files:
                    if file.endswith(regexp):
                        mp4_files.append(os.path.join(sub_root, file))
        # for file in files:
        #     if file.endswith('.mp4'):
        #         mp4_files.append(os.path.join(root, file))
    return sorted(mp4_files)


if __name__ == '__main__':
    base_dir = "/Users/wenchen/workspace/py_project/ProPainter"
    dir = base_dir + "/inputs/video_merge_test"
    ot_path = base_dir + "/inputs/video_merge_test"
    split_video(dir + '/running_car.mp4', f"{ot_path}/output", 3)
    merge_videos(ot_path, dir + '/video_merge.mp4', True)
