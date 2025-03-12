import frida
import os
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

# 创建线程锁用于打印和文件操作
print_lock = threading.Lock()
file_lock = threading.Lock()

def decrypt_file(args):
    file, root, i, num, output_dir, script = args
    try:
        file_path = os.path.splitext(file)
        
        # 只处理 .mflac 和 .mgg 文件
        if file_path[-1] in [".mflac", ".mgg"]:
            with print_lock:
                print(f"Decrypting {i}/{num}", file)
            
            # 修改文件扩展名
            file_path = list(file_path)
            file_path[-1] = file_path[-1].replace("mflac", "flac").replace("mgg", "ogg")
            file_path_str = "".join(file_path)
            
            # 检查解密文件是否已经存在
            output_file_path = os.path.join(output_dir, file_path_str)
            if os.path.exists(output_file_path):
                with print_lock:
                    print(f"{i}/{num} File {output_file_path} 已存在，跳过.")
                return

            tmp_file_path = hashlib.md5(file.encode()).hexdigest()
            tmp_file_path = os.path.join(output_dir, tmp_file_path)
            tmp_file_path = os.path.abspath(tmp_file_path)
            
            # 使用文件锁保护解密和重命名操作
            with file_lock:
                # 调用脚本中的 decrypt 方法解密文件
                data = script.exports_sync.decrypt(os.path.join(root, file), tmp_file_path)
                # 重命名临时文件
                os.rename(tmp_file_path, output_file_path)
    except Exception as e:
        with print_lock:
            print(f"Error processing {file}: {str(e)}")

# 挂钩 QQ 音乐进程
session = frida.attach("QQMusic.exe")

# 加载并执行 JavaScript 脚本
script = session.create_script(open("hook_qq_music.js", "r", encoding="utf-8").read())
script.load()


# 创建输出目录
# output_dir = str(Path.home()) + "\\Music"
output_dir = "D:\\Music"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 获取用户音乐目录路径
# home = str(Path.home()) + "\\Music\\VipSongsDownload"
home = "C:\\Users\\litsev\\Music\\VipSongsDownload"
home = os.path.abspath(home)

try:
    # 收集需要处理的文件
    files_to_process = []
    for root, dirs, files in os.walk(home):
        # 计算目标文件数量
        num = sum(1 for file in files if os.path.splitext(file)[1] in [".mflac", ".mgg"])
        current_count = 0
        
        # 只处理目标文件并正确计数
        for file in files:
            if os.path.splitext(file)[1] in [".mflac", ".mgg"]:
                current_count += 1
                files_to_process.append((file, root, current_count, num, output_dir, script))

    # 使用线程池处理文件
    with ThreadPoolExecutor(max_workers=24) as executor:
        executor.map(decrypt_file, files_to_process)

finally:
    # 确保会话被正确分离
    session.detach()
