import os
import subprocess
import traceback

from celery import Celery, current_task
import requests
from fastapi import HTTPException
from qiniu import Auth, put_file, etag, BucketManager
import sys

from utils import video_util

root_dir = sys.path[0]
destination = root_dir + "/inputs/remove_logo"
output_name = "inpaint_out.mp4"
os.makedirs(destination, exist_ok=True)
notify_url = "https://api.aijijiang.com/backend_task/notify/complete"
# notify_url = "http://api-test.aijijiang.com/backend_task/notify/complete"
# 需要填写你的 Access Key 和 Secret Key
access_key = 'O5X1WeHugGmzA2-1oS32qPh1pkypNVWJ2ksJ4Hlc'
secret_key = 'mXWg4Q1tUV6g3y_SGGBGFqOLfW2TI5iJoVcUlHJ1'
# 构建鉴权对象
q = Auth(access_key, secret_key)
bucket = BucketManager(q)
# 要上传的空间
bucket_name = 'ai-haoyin'

app = Celery('tasks',
             broker='redis://default:Jizhijiangxin_Haoyin_2023@14.22.82.3:30101/2',
             backend='redis://default:Jizhijiangxin_Haoyin_2023@14.22.82.3:30101/2')
app.conf.setdefault("worker_concurrency", 1)
app.conf.setdefault("worker_prefetch_multiplier", 1)
app.conf.setdefault("task_acks_late", True)
app.conf.setdefault("result_expires", 36000)
app.conf.setdefault("REDIS_BACKEND_HEALTH_CHECK_INTERVAL", 5)
app.conf.setdefault("broker_connection_retry_on_startup", True)


@app.task
def background_task(request: dict):
    taskid = current_task.request.id
    try:
        image_path = downloadFile(request['image_path'])
        video_path = downloadFile(request['video_path'])
        video_name = getFileName(video_path)
        output_dir = f"results/{taskid}"
        os.makedirs(output_dir, exist_ok=True)
        print("开始执行去水印任务。")
        args = ['python', 'inference_propainter.py',
                '--video', video_path,
                '--mask', image_path,
                '--output', output_dir,
                # '--subvideo_length', '56',
                # '--neighbor_length', '7',
                # '--ref_stride', '13',
                # '--resize_ratio', '0.5',
                '--fp16']
        output = subprocess.run(args, capture_output=True, text=True)
        print(output)
        if output.returncode == 0:
            # upload
            video_url = uploadQiniu(output_dir, taskid, video_name)
            # notify success
            resp = requests.post(notify_url,
                                 json={"backendTaskId": taskid, "taskType": 1, "success": True, "resultUrl": video_url})
            print(f"{taskid} 去水印任务已经完成")
            if resp.status_code == 200:
                result = resp.text
                print(result)
                # if result["code"] != "10000":
                #     print(f"{task_id} 更新任务状态失败。原因: {result}")

            else:
                print(f"{taskid} 更新任务状态失败，code: {resp.status_code}, message: {resp.reason}")

        else:
            print(f"{taskid} 执行异常，请及时处理错误: {output}")
            # notify error
            resp = requests.post(notify_url, json={"backendTaskId": taskid, "taskType": 1, "success": False,
                                                   "reason": "执行去水印任务失败，请及时联系管理员处理"})
            if resp.status_code != 200:
                print(f"{taskid} 更新任务状态失败，code: {resp.status_code}, message: {resp.reason}")

    except Exception:
        print(f"{taskid} 执行异常，请及时处理异常: {Exception}")

        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)


@app.task
def background_taskV2(request: dict):
    taskid = current_task.request.id
    try:
        image_path = downloadFile(request['image_path'])
        video_path = downloadFile(request['video_path'])

        output_dir = f"results/{taskid}"
        split_output_dir = f"results/{taskid}/split"
        os.makedirs(output_dir, exist_ok=True)
        # split
        split_videos = video_util.split_video(video_path, split_output_dir, 5)
        print(f"分割后的视频文件: {split_videos}")
        print("开始执行去水印任务。")
        for video in split_videos:
            print(f"正在执行 {video}去水印。")
            video_name = getFileName(video)
            removeLogo(image_path, split_output_dir, taskid, video_name, video)
            print(f"{video}去水印执行成功。")
        #merge
        print("开始执行视频合并任务。")
        video_util.merge_videos(f"{root_dir}/{split_output_dir}", f"{output_dir}/{output_name}", True, output_name)
        # upload
        video_url = uploadQiniuV2(output_dir, taskid)
        # notify success
        resp = requests.post(notify_url,
                             json={"backendTaskId": taskid, "taskType": 1, "success": True, "resultUrl": video_url})
        if resp.status_code == 200:
            result = resp.text
            print(result)
            # if result["code"] != "10000":
            #     print(f"{task_id} 更新任务状态失败。原因: {result}")

        else:
            print(f"{taskid} 更新任务状态失败，code: {resp.status_code}, message: {resp.reason}")
        print(f"{taskid} 去水印任务已经完成")
    except Exception:
        print(f"{taskid} 执行异常，请及时处理异常: {Exception}")
        # notify error
        resp = requests.post(notify_url, json={"backendTaskId": taskid, "taskType": 1, "success": False,
                                               "reason": "执行去水印任务失败，请及时联系管理员处理"})
        if resp.status_code != 200:
            print(f"{taskid} 更新任务状态失败，code: {resp.status_code}, message: {resp.reason}")

        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)


def removeLogo(image_path, output_dir, taskid, video_name, video_path):
    args = ['python', 'inference_propainter.py',
            '--video', video_path,
            '--mask', image_path,
            '--output', output_dir,
            # '--subvideo_length', '56',
            # '--neighbor_length', '7',
            # '--ref_stride', '13',
            # '--resize_ratio', '0.5',
            '--fp16']
    output = subprocess.run(args, capture_output=True, text=True)
    if output.returncode != 0:
        print(f"{taskid} 执行异常，请及时处理错误: {output}")
        raise RuntimeError(output)


def uploadQiniu(output_dir, taskid, video_name):
    # 上传后保存的文件名
    key = f"remove_logo/{taskid}/{output_name}"
    # 生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, key, 3600)
    # 要上传文件的本地路径
    local_file = f"{root_dir}/{output_dir}/{video_name[:video_name.rindex('.')]}/{output_name}"
    ret, info = put_file(token, key, local_file, version='v2')
    print(info)
    assert ret['key'] == key
    assert ret['hash'] == etag(local_file)
    # 更新的生命周期
    days = '60'
    ret, info = bucket.delete_after_days(bucket_name, key, days)
    print(info)
    return key


def uploadQiniuV2(output_dir, taskid):
    # 上传后保存的文件名
    key = f"remove_logo/{taskid}/{output_name}"
    # 生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, key, 3600)
    # 要上传文件的本地路径
    local_file = f"{root_dir}/{output_dir}/{output_name}"
    ret, info = put_file(token, key, local_file, version='v2')
    print(info)
    assert ret['key'] == key
    assert ret['hash'] == etag(local_file)
    # 更新的生命周期
    days = '60'
    ret, info = bucket.delete_after_days(bucket_name, key, days)
    print(info)
    return key


def downloadFile(filePath: str) -> str:
    try:
        file_name = getFileName(filePath)
        dump_path = destination + file_name
        resp = requests.get(filePath, stream=True)
        if resp.status_code == 200:
            # 打开目标文件进行写入
            with open(dump_path, 'wb') as file:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            print(f"文件已成功下载并保存到 {dump_path}")
            return dump_path
        else:
            print(f"下载文件失败，文件路径: {filePath} code: {resp.status_code}, message: {resp.reason}")
    except Exception:
        raise HTTPException(status_code=500, detail="文件下载异常，请检查文件是否能正常下载")


def getFileName(fileName: str):
    if fileName is not None and len(fileName) > 0:
        return fileName[fileName.rindex("/"):]

