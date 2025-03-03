import os
import sys
from PIL import Image
from io import BytesIO
import shutil
from tqdm import tqdm

    
   
def optimize_image(image_path, max_size_mb=5, quality=85, step=5):
    """优化图片文件大小"""
    max_size = max_size_mb * 1024 * 1024
    original_size = os.path.getsize(image_path)
    
    if original_size <= max_size:
        return False
    
    with Image.open(image_path) as img:
        format = img.format
        # 转换颜色模式优化文件大小
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 渐进式压缩
        while quality > 10 and original_size > max_size:
            buffer = BytesIO()
            save_args = {
                'format': format,
                'quality': quality,
                'optimize': True
            }
            
            # JPEG特殊处理
            if format == 'JPEG':
                img.save(buffer, **save_args, progressive=True)
            else:
                img.save(buffer, **save_args)
            
            if buffer.tell() <= max_size:
                break
            
            quality -= step
        
        # 保存优化后的文件
        if buffer.tell() < original_size:
            with open(image_path, 'wb') as f:
                f.write(buffer.getvalue())
            return True
        return False

def process_large_files(image_root, log_file, max_size_mb=5):
    processed = set()
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            processed = set(line.strip() for line in f)
    compressed_log = "compressed.log"
    problem_log = "compression_problems.log"
    compression_count = 0

    # 初始化日志文件（如果不存在）
    for f in [compressed_log, problem_log]:
        if not os.path.exists(f):
            open(f, 'w').close()
    with tqdm(desc="扫描大文件", unit="文件") as scan_pbar:
        for root, _, files in os.walk(image_root):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    rel_path = os.path.relpath(os.path.join(root, file), image_root)
                    scan_pbar.update(1)
                    if rel_path not in processed:
                        abs_path = os.path.join(image_root, rel_path)
                        try:
                            file_size = os.path.getsize(abs_path)
                            if file_size > max_size_mb * 1024 * 1024:
                                print(f"压缩中: {rel_path} ({file_size//1024}KB)")
                                if optimize_image(abs_path, max_size_mb):
                                    new_size = os.path.getsize(abs_path)
                                    with open(compressed_log, "a") as f:
                                        f.write(f"{rel_path}\t原始大小:{file_size}\t处理后:{os.path.getsize(abs_path)}\n")
                                    compression_count += 1
                                else:
                                    with open(problem_log, "a") as f:
                                        f.write(f"{rel_path}\t无法压缩\n")
                        except Exception as e:
                            print(f"处理失败 {rel_path}: {str(e)}")
                            with open(problem_log, "a") as f:
                                f.write(f"{rel_path}\t错误:{str(e)}\n")

if __name__ == "__main__":
    image_root = "存放图片的最顶层根目录"
    log_file = "processed.log" #
    
    # 设置系统文件句柄限制（Linux/MacOS）
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_NOFILE, (65536, 65536))
    except ImportError:
        pass
    
    process_large_files(
        image_root=image_root,
        log_file=log_file,
        max_size_mb=5
    )