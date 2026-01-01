import os
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import argparse
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


class FileOrganizer:
    def __init__(self, source_dir, target_dir=None, dry_run=False, remove_duplicates=False, include_brand=False, max_workers=4):
        """
        初始化文件整理器
        
        Args:
            source_dir: 源文件夹路径
            target_dir: 目标文件夹路径，如果为None则在源文件夹下创建organized文件夹
            dry_run: 是否为预览模式，不实际移动文件
            remove_duplicates: 是否删除重复文件
            include_brand: 是否在文件名中包含相机品牌
            max_workers: 最大线程数
        """
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir) if target_dir else self.source_dir / "organized"
        self.dry_run = dry_run
        self.remove_duplicates = remove_duplicates
        self.include_brand = include_brand
        self.max_workers = max_workers
        self.lock = threading.Lock()
        self.processed_count = 0
        self.error_count = 0
        self.failed_files = []
        self.failed_dir = self.target_dir.parent / "failed_files" if target_dir else self.source_dir / "failed_files"
        
        if not self.source_dir.exists():
            raise ValueError(f"源文件夹不存在: {self.source_dir}")
        
        if self.include_brand and not PILLOW_AVAILABLE:
            print("警告: 未安装Pillow库，无法提取相机品牌信息。请运行: pip install Pillow")
            self.include_brand = False
    
    def get_file_modified_date(self, file_path):
        """获取文件的最后修改时间"""
        timestamp = os.path.getmtime(file_path)
        return datetime.fromtimestamp(timestamp)
    
    def extract_camera_brand(self, file_path):
        """
        从图片EXIF数据中提取相机品牌
        
        Args:
            file_path: 图片文件路径
        
        Returns:
            相机品牌名称，如果无法提取则返回None
        """
        if not PILLOW_AVAILABLE:
            return None
        
        try:
            image = Image.open(file_path)
            exif_data = image._getexif()
            
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == "Make":
                        # 清理品牌名称，移除多余空格和特殊字符
                        brand = str(value).strip()
                        # 移除常见的后缀
                        brand = brand.replace('CORPORATION', '').replace('Corporation', '').strip()
                        # 清理非法字符
                        brand = self.sanitize_filename(brand)
                        return brand if brand else None
        except Exception:
            pass
        
        return None
    
    def sanitize_filename(self, filename):
        """
        清理文件名，移除空字符和其他非法字符
        
        Args:
            filename: 原始文件名
        
        Returns:
            清理后的文件名
        """
        if not filename:
            return "unnamed"
        
        # 移除空字符和其他控制字符（ASCII < 32）
        sanitized = ''.join(char for char in filename if ord(char) >= 32 and char != '\x00')
        
        # 移除Windows文件名中的非法字符
        invalid_chars = '<>:"|?*\\/\r\n\t'
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # 移除前后空格和点
        sanitized = sanitized.strip('. ')
        
        # 如果清理后为空，使用默认名称
        if not sanitized:
            return "unnamed"
        
        return sanitized
    
    def calculate_file_hash(self, file_path, block_size=65536):
        """
        计算文件的MD5哈希值
        
        Args:
            file_path: 文件路径
            block_size: 读取块大小
        
        Returns:
            文件的MD5哈希值
        """
        md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(block_size)
                    if not data:
                        break
                    md5.update(data)
            return md5.hexdigest()
        except Exception as e:
            print(f"  警告: 无法计算文件哈希 {file_path.name} - {e}")
            return None
    
    def scan_files_recursive(self):
        """
        递归扫描所有文件（包括子文件夹），带错误处理
        
        Returns:
            文件路径列表
        """
        files = []
        error_count = 0
        
        def scan_directory(path):
            nonlocal error_count
            try:
                for item in path.iterdir():
                    try:
                        if item.is_file():
                            # 验证文件路径是否有效
                            try:
                                item.stat()
                                files.append(item)
                            except (OSError, PermissionError):
                                error_count += 1
                        elif item.is_dir():
                            scan_directory(item)
                    except (OSError, PermissionError):
                        error_count += 1
            except (OSError, PermissionError):
                error_count += 1
        
        scan_directory(self.source_dir)
        
        if error_count > 0:
            print(f"\n警告: {error_count} 个路径无法访问，已自动跳过")
        
        return files
    
    def calculate_hash_worker(self, file_path):
        """多线程哈希计算工作函数"""
        try:
            file_hash = self.calculate_file_hash(file_path)
            return (file_path, file_hash)
        except Exception as e:
            return (file_path, None)
    
    def find_duplicates(self):
        """
        查找重复文件（多线程）
        
        Returns:
            字典，key为文件哈希，value为具有相同哈希的文件路径列表
        """
        hash_map = defaultdict(list)
        
        print("\n正在递归扫描文件并计算哈希值...")
        all_files = self.scan_files_recursive()
        total_files = len(all_files)
        print(f"找到 {total_files} 个文件，开始计算哈希值...")
        
        file_count = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.calculate_hash_worker, f): f for f in all_files}
            
            for future in as_completed(futures):
                file_path, file_hash = future.result()
                if file_hash:
                    hash_map[file_hash].append(file_path)
                    file_count += 1
                    
                    if file_count % 1000 == 0:
                        print(f"  已处理 {file_count}/{total_files} 个文件...")
        
        print(f"已扫描 {file_count} 个文件")
        
        duplicates = {k: v for k, v in hash_map.items() if len(v) > 1}
        return duplicates
    
    def remove_duplicate_files(self):
        """
        删除重复文件，保留最早的文件（根据修改时间）
        
        Returns:
            删除的文件数量
        """
        duplicates = self.find_duplicates()
        
        if not duplicates:
            print("\n未发现重复文件")
            return 0
        
        total_duplicates = sum(len(files) - 1 for files in duplicates.values())
        print(f"\n发现 {len(duplicates)} 组重复文件，共 {total_duplicates} 个重复项")
        
        if self.dry_run:
            print("\n【预览模式】以下文件将被删除:\n")
        else:
            print("\n正在删除重复文件...\n")
        
        deleted_count = 0
        total_size_saved = 0
        
        for file_hash, files in duplicates.items():
            files_with_dates = [(f, self.get_file_modified_date(f)) for f in files]
            files_with_dates.sort(key=lambda x: x[1])
            
            keep_file = files_with_dates[0][0]
            duplicates_to_remove = files_with_dates[1:]
            
            print(f"保留: {keep_file.name} ({files_with_dates[0][1].strftime('%Y-%m-%d %H:%M:%S')})")
            
            for dup_file, dup_date in duplicates_to_remove:
                file_size = dup_file.stat().st_size
                print(f"  删除: {dup_file.name} ({dup_date.strftime('%Y-%m-%d %H:%M:%S')}) - {self.format_size(file_size)}")
                
                if not self.dry_run:
                    try:
                        dup_file.unlink()
                        deleted_count += 1
                        total_size_saved += file_size
                    except Exception as e:
                        print(f"    错误: 删除失败 - {e}")
            print()
        
        if not self.dry_run:
            print(f"完成! 删除了 {deleted_count} 个重复文件，节省空间 {self.format_size(total_size_saved)}")
        else:
            estimated_size = sum(f.stat().st_size for files in duplicates.values() for f in files[1:])
            print(f"预览完成! 将删除 {total_duplicates} 个重复文件，预计节省空间 {self.format_size(estimated_size)}")
        
        return deleted_count
    
    def find_available_sequence(self, month_dir, date, extension, start_seq=1, brand=None):
        """
        查找可用的序号，如果文件已存在则自动递增
        
        Args:
            month_dir: 月份目录
            date: 日期对象
            extension: 文件扩展名
            start_seq: 起始序号
            brand: 相机品牌（可选）
        
        Returns:
            可用的序号和对应的文件名
        """
        seq = start_seq
        while True:
            new_filename = self.generate_new_filename(date, seq, extension, brand)
            new_path = month_dir / new_filename
            if not new_path.exists():
                return seq, new_filename
            seq += 1
            if seq > 999:
                raise ValueError(f"序号超出范围（最大999）: {date.strftime('%Y%m%d')}")
    
    @staticmethod
    def format_size(size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def process_file_info(self, file_path):
        """多线程文件信息处理工作函数"""
        try:
            modified_date = self.get_file_modified_date(file_path)
            year_month = (modified_date.year, modified_date.month)
            
            brand = None
            if self.include_brand:
                brand = self.extract_camera_brand(file_path)
            
            return {
                'path': file_path,
                'date': modified_date,
                'extension': file_path.suffix,
                'brand': brand,
                'year_month': year_month
            }
        except Exception as e:
            with self.lock:
                self.failed_files.append((str(file_path), str(e)))
            return None
    
    def group_files_by_date(self):
        """按年月分组文件（递归扫描所有子文件夹，多线程处理）"""
        files_by_date = defaultdict(list)
        
        print("\n正在递归扫描文件夹...")
        all_files = self.scan_files_recursive()
        total_files = len(all_files)
        print(f"找到 {total_files} 个文件，开始分析...")
        
        processed = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.process_file_info, f): f for f in all_files}
            
            for future in as_completed(futures):
                file_info = future.result()
                if file_info:
                    year_month = file_info.pop('year_month')
                    files_by_date[year_month].append(file_info)
                    processed += 1
                    
                    if processed % 1000 == 0:
                        print(f"  已分析 {processed}/{total_files} 个文件...")
        
        print(f"分析完成，共 {processed} 个文件")
        
        for year_month in files_by_date:
            files_by_date[year_month].sort(key=lambda x: x['date'])
        
        return files_by_date
    
    
    def generate_new_filename(self, date, sequence, extension, brand=None):
        """
        生成新文件名
        
        Args:
            date: datetime对象
            sequence: 序号
            extension: 文件扩展名
            brand: 相机品牌（可选）
        
        Returns:
            新文件名，格式为 Brand_yyyymmdd00x.ext 或 yyyymmdd00x.ext
        """
        date_str = date.strftime('%Y%m%d')
        seq_str = f"{sequence:03d}"
        
        # 清理扩展名
        extension = self.sanitize_filename(extension) if extension else ""
        if extension and not extension.startswith('.'):
            extension = '.' + extension
        
        # 清理品牌名称
        if brand:
            brand = self.sanitize_filename(brand)
            return f"{brand}_{date_str}{seq_str}{extension}"
        
        return f"{date_str}{seq_str}{extension}"
    
    def organize_files(self):
        """执行文件整理"""
        # 先整理文件
        files_by_date = self.group_files_by_date()
        
        if not files_by_date:
            print("未找到需要整理的文件")
            return
        
        total_files = sum(len(files) for files in files_by_date.values())
        print(f"找到 {total_files} 个文件需要整理")
        print(f"目标目录: {self.target_dir}")
        
        if self.dry_run:
            print("\n【预览模式】不会实际移动文件\n")
        
        moved_count = 0
        conflict_count = 0
        
        for (year, month), files in sorted(files_by_date.items()):
            year_dir = self.target_dir / str(year)
            month_dir = year_dir / f"{month:02d}"
            
            print(f"\n处理 {year}年{month}月 的 {len(files)} 个文件...")
            
            if not self.dry_run:
                month_dir.mkdir(parents=True, exist_ok=True)
            
            files_by_day = defaultdict(list)
            for file_info in files:
                day = file_info['date'].day
                files_by_day[day].append(file_info)
            
            file_index = 0
            for day, day_files in sorted(files_by_day.items()):
                for seq, file_info in enumerate(day_files, start=1):
                    old_path = file_info['path']
                    brand = file_info.get('brand')
                    
                    actual_seq, new_filename = self.find_available_sequence(
                        month_dir,
                        file_info['date'],
                        file_info['extension'],
                        seq,
                        brand
                    )
                    new_path = month_dir / new_filename
                    
                    file_index += 1
                    # 每1000个文件打印一次日志
                    if file_index % 1000 == 0:
                        print(f"  已处理 {file_index}/{len(files)} 个文件...")
                    elif actual_seq != seq:
                        print(f"  序号冲突，自动调整: {old_path.name} -> {year}/{month:02d}/{new_filename} (序号 {seq} -> {actual_seq})")
                        conflict_count += 1
                    
                    if not self.dry_run:
                        try:
                            shutil.move(str(old_path), str(new_path))
                            moved_count += 1
                        except Exception as e:
                            print(f"  错误: 移动文件失败 - {e}")
                            with self.lock:
                                self.failed_files.append((str(old_path), str(e)))
        
        if not self.dry_run:
            print(f"\n完成! 成功整理 {moved_count} 个文件")
            if conflict_count > 0:
                print(f"其中 {conflict_count} 个文件因序号冲突自动调整了序号")
            
            # 处理失败的文件
            if self.failed_files:
                self.handle_failed_files()
            
            # 整理完成后再删除重复文件
            if self.remove_duplicates:
                print("\n" + "="*50)
                print("整理完成，开始检测并删除重复文件...")
                print("="*50 + "\n")
                self.remove_duplicates_from_organized()
            
            # 显示任务完成总结
            print("\n" + "="*60)
            print("🎉 所有任务已完成！")
            print("="*60)
            print(f"✅ 成功整理: {moved_count} 个文件")
            if conflict_count > 0:
                print(f"⚠️  序号调整: {conflict_count} 个文件")
            if self.failed_files:
                print(f"❌ 处理失败: {len(self.failed_files)} 个文件")
            print(f"📁 目标目录: {self.target_dir}")
            print("="*60)
        else:
            print(f"\n预览完成! 共 {total_files} 个文件将被整理")
            if conflict_count > 0:
                print(f"其中 {conflict_count} 个文件将因序号冲突自动调整序号")
            print("\n提示: 使用不带 --dry-run 参数运行以实际执行整理操作")
    
    def handle_failed_files(self):
        """处理失败的文件，移动到failed_files文件夹"""
        if not self.failed_files:
            return
        
        print(f"\n处理 {len(self.failed_files)} 个失败的文件...")
        
        try:
            self.failed_dir.mkdir(parents=True, exist_ok=True)
            
            # 写入错误日志
            log_file = self.failed_dir / "error_log.txt"
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"文件整理错误日志 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*80 + "\n\n")
                for file_path, error in self.failed_files:
                    f.write(f"文件: {file_path}\n")
                    f.write(f"错误: {error}\n")
                    f.write("-"*80 + "\n")
            
            print(f"错误日志已保存到: {log_file}")
            print(f"失败文件目录: {self.failed_dir}")
            
            # 尝试移动失败的文件
            moved = 0
            for file_path, error in self.failed_files:
                try:
                    src = Path(file_path)
                    if src.exists():
                        dst = self.failed_dir / src.name
                        # 如果目标文件已存在，添加时间戳
                        if dst.exists():
                            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                            dst = self.failed_dir / f"{src.stem}_{timestamp}{src.suffix}"
                        shutil.move(str(src), str(dst))
                        moved += 1
                except Exception as e:
                    pass  # 如果移动失败，忽略
            
            if moved > 0:
                print(f"已将 {moved} 个失败文件移动到: {self.failed_dir}")
        
        except Exception as e:
            print(f"警告: 无法创建失败文件目录 - {e}")
    
    def remove_duplicates_from_organized(self):
        """从已整理的文件中删除重复文件（仅在同一文件夹内对比）"""
        print("正在扫描已整理的文件并计算哈希值...")
        
        # 按文件夹分组扫描
        folders = []
        for year_dir in self.target_dir.iterdir():
            if year_dir.is_dir():
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir():
                        folders.append(month_dir)
        
        if not folders:
            print("\n未找到已整理的文件夹")
            return
        
        print(f"找到 {len(folders)} 个文件夹，开始逐个文件夹检测重复...")
        
        total_deleted = 0
        total_size_saved = 0
        total_duplicates_found = 0
        
        for folder in folders:
            # 获取当前文件夹中的所有文件
            folder_files = [f for f in folder.iterdir() if f.is_file()]
            
            if len(folder_files) < 2:
                continue  # 少于2个文件，不可能有重复
            
            # 计算当前文件夹中所有文件的哈希值
            hash_map = defaultdict(list)
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self.calculate_hash_worker, f): f for f in folder_files}
                
                for future in as_completed(futures):
                    file_path, file_hash = future.result()
                    if file_hash:
                        hash_map[file_hash].append(file_path)
            
            # 查找当前文件夹中的重复文件
            folder_duplicates = {k: v for k, v in hash_map.items() if len(v) > 1}
            
            if not folder_duplicates:
                continue
            
            # 显示当前文件夹信息
            folder_dup_count = sum(len(files) - 1 for files in folder_duplicates.values())
            total_duplicates_found += folder_dup_count
            print(f"\n{folder.parent.name}/{folder.name} - 发现 {len(folder_duplicates)} 组重复文件，共 {folder_dup_count} 个重复项")
            
            # 删除重复文件
            for file_hash, file_list in folder_duplicates.items():
                # 按修改时间排序，保留最早的
                sorted_files = sorted(file_list, key=lambda x: x.stat().st_mtime)
                keep_file = sorted_files[0]
                delete_files = sorted_files[1:]
                
                keep_time = datetime.fromtimestamp(keep_file.stat().st_mtime)
                print(f"  保留: {keep_file.name} ({keep_time.strftime('%Y-%m-%d %H:%M:%S')})")
                
                for dup_file in delete_files:
                    try:
                        file_size = dup_file.stat().st_size
                        dup_time = datetime.fromtimestamp(dup_file.stat().st_mtime)
                        dup_file.unlink()
                        total_deleted += 1
                        total_size_saved += file_size
                        print(f"    删除: {dup_file.name} ({dup_time.strftime('%Y-%m-%d %H:%M:%S')}) - {self.format_size(file_size)}")
                    except Exception as e:
                        print(f"    错误: 无法删除 {dup_file.name} - {e}")
        
        if total_duplicates_found == 0:
            print("\n未发现重复文件")
        else:
            print(f"\n完成! 删除了 {total_deleted} 个重复文件，节省空间 {self.format_size(total_size_saved)}")


def main():
    parser = argparse.ArgumentParser(
        description='根据文件修改时间整理文件到年/月文件夹，并按日期序号重命名',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python file_organizer.py D:\\RecoveredFiles
  python file_organizer.py D:\\RecoveredFiles -o D:\\Organized
  python file_organizer.py D:\\RecoveredFiles --dry-run
  python file_organizer.py D:\\RecoveredFiles --remove-duplicates
  python file_organizer.py D:\\RecoveredFiles --remove-duplicates --dry-run
        """
    )
    
    parser.add_argument('source', help='源文件夹路径')
    parser.add_argument('-o', '--output', help='输出文件夹路径（默认为源文件夹下的organized目录）')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际移动文件')
    parser.add_argument('--remove-duplicates', action='store_true', help='删除重复文件（基于文件内容哈希比对）')
    parser.add_argument('--include-brand', action='store_true', help='在文件名中包含相机品牌（需要Pillow库）')
    parser.add_argument('--threads', type=int, default=4, help='线程数（默认4）')
    
    args = parser.parse_args()
    
    try:
        organizer = FileOrganizer(args.source, args.output, args.dry_run, args.remove_duplicates, args.include_brand, args.threads)
        organizer.organize_files()
        print("\n程序已正常退出")
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        return 1
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
