import os
import base64
import cv2
import requests
from tqdm import tqdm
import json
import hashlib

def process_image_pipeline(img_path):
    """单张图片处理流水线"""
    # 1. 读取图片并编码base64
    with open(img_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    
    # 2. 发送检测请求
    try:
        response = requests.post(
            url="http://0.0.0.0:4044/detect",
            headers={"Content-Type": "application/json"},
            json={"image_base64": data},
            timeout=10  
        ).json()
    except Exception as e:
        print(f"请求失败：{str(e)}")
        return False
    
    # 3. OpenCV处理图像
    img = cv2.imread(img_path)
    for box, cls in zip(response['pred_boxes'], response['pred_classes']):
        if cls == 0:
            x_min, y_min, x_max, y_max = map(int, box)
            # 边界检查（网页2建议）
            height, width = img.shape[:2]
            x_min = max(0, min(x_min, width-1))
            y_min = max(0, min(y_min, height-1))
            x_max = max(0, min(x_max, width-1))
            y_max = max(0, min(y_max, height-1))
            cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (0,0,0), -1)
    
    # 4. 覆盖保存原图
    cv2.imwrite(img_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 100])  # 保持JPEG质量
    return True


# 记录已处理的图片 
class SimpleTracker:
    def __init__(self, log_file="progress.json"):
        self.log_file = log_file
        self.progress = {}
        if os.path.exists(log_file):
            with open(log_file) as f:
                self.progress = json.load(f)
    
    def is_processed(self, filepath):
        return self.progress.get(filepath, False)
    
    def mark_done(self, filepath):
        self.progress[filepath] = True
        with open(self.log_file, 'w') as f:
            json.dump(self.progress, f, indent=2)

def batch_process_folder(root_folder):
    """批量处理文件夹"""
    tracker = SimpleTracker()
    # 获取所有图片文件
    image_exts = ('.jpg', '.jpeg', '.png', '.bmp')
    all_files = [
        os.path.join(root, f) 
        for root, _, files in os.walk(root_folder)
        for f in files if f.lower().endswith(image_exts)
    ]
    pending_files = [f for f in all_files if not tracker.is_processed(f)]
   
    
    # 处理进度显示
    with tqdm(total=len(pending_files), desc="处理进度") as pbar:
        for img_path in pending_files:
            try:
                if process_image_pipeline(img_path):
                    tracker.mark_done(img_path)
            except Exception as e:
                print(f"处理失败：{img_path} ({str(e)})")
                continue

if __name__ == "__main__":
    # 设置代理（根据网页1的环境变量设置）
    os.environ['http_proxy'] = ''
    os.environ['https_proxy'] = ''
    
    # 启动处理（输入你的图片根目录）
    batch_process_folder("")
