# File Organizer Tool

Automatically organize files into `year/month` folder structure based on their last modified time, and rename them using the `yyyymmdd00x` format.

## Features

- 📁 Automatically create year/month folder structure
- 📅 Classify files based on last modified time
- 🔄 Rename files by date and sequence (format: yyyymmdd001, yyyymmdd002...)
- 🔍 **Smart Deduplication**: Identify and remove duplicate files based on content hash
- 👀 Preview mode support - check effects before execution
- 🔒 Preserve original file extensions
- 🔢 **Smart Sequence Adjustment**: Auto-increment sequence numbers when target files exist, ensuring all files are organized
- 📷 **Brand Recognition**: Optionally extract camera brand from image EXIF data and add to filename
- 🗂️ **Recursive Processing**: Automatically traverse all subfolders and process files at all levels
- ⚡ **Multi-threading**: Support concurrent processing for significantly improved speed
- 📊 **Batch Logging**: Print progress every 1000 files to avoid excessive logs
- 🛡️ **Error Tolerance**: Automatically skip inaccessible files or folders and continue processing
- 📝 **Failed File Handling**: Automatically log errors and move failed files to dedicated directory
- 🔄 **Optimized Workflow**: Organize files first, then remove duplicates to avoid impacting organization performance

## Usage

### Basic Usage

```bash
python file_organizer.py <source_folder_path>
```

This will create an `organized` directory in the source folder and organize files into it.

### Specify Output Directory

```bash
python file_organizer.py <source_folder_path> -o <output_folder_path>
python file_organizer.py H:\picture\failed_files -o H:\picture\organized --remove-duplicates --include-brand --threads 8
```

### Preview Mode (Recommended for First Use)

```bash
python file_organizer.py <source_folder_path> --dry-run
```

Preview mode displays operations to be performed without actually moving files.

### Remove Duplicate Files

```bash
python file_organizer.py <source_folder_path> --remove-duplicates
```

The program identifies files with identical content by calculating MD5 hash values, even if filenames differ. It keeps the file with the earliest modification time and deletes other duplicates.

### Include Camera Brand Information

```bash
python file_organizer.py <source_folder_path> --include-brand
```

The program extracts camera brand (e.g., Canon, Nikon, Sony) from image EXIF data and adds it to the filename.

**Note**: This feature requires Pillow library:
```bash
pip install Pillow
```

### Multi-threading Processing

```bash
# Use default 4 threads
python file_organizer.py <source_folder_path>

# Specify thread count (adjust based on CPU cores)
python file_organizer.py <source_folder_path> --threads 8
```

Multi-threading significantly improves processing speed for large file sets, especially for:
- Calculating file hashes (deduplication feature)
- Extracting EXIF data (brand recognition feature)
- Analyzing file information

**Recommended thread count**:
- Less than 1000 files: Use default 4 threads
- 1000-10000 files: Use 8 threads
- Over 10000 files: Use 8-16 threads

### Combined Usage

```bash
# Preview organization effect
python file_organizer.py <source_folder_path> --dry-run

# Organize files
python file_organizer.py <source_folder_path>

# Organize + deduplicate (organize first, then remove duplicates)
python file_organizer.py <source_folder_path> --remove-duplicates

# Organize + deduplicate + brand recognition
python file_organizer.py <source_folder_path> --remove-duplicates --include-brand

# Use 8 threads to accelerate processing
python file_organizer.py <source_folder_path> --threads 8 --remove-duplicates
```

## Usage Examples

### Example 1: Organize Recovered Files

```bash
python file_organizer.py D:\RecoveredFiles
```

Result:
```
D:\RecoveredFiles\organized\
├── 2023\
│   ├── 01\
│   │   ├── 20230115001.jpg
│   │   ├── 20230115002.jpg
│   │   └── 20230128001.pdf
│   └── 02\
│       ├── 20230201001.docx
│       └── 20230215001.jpg
└── 2024\
    └── 12\
        ├── 20241201001.png
        └── 20241201002.png
```

### Example 2: Specify Output Directory

```bash
python file_organizer.py D:\RecoveredFiles -o D:\OrganizedFiles
```

### Example 3: Preview Before Execution

```bash
# Step 1: Preview
python file_organizer.py D:\RecoveredFiles --dry-run

# Step 2: Execute after confirmation
python file_organizer.py D:\RecoveredFiles
```

### Example 4: Organize and Remove Duplicates

```bash
# Organize files and remove duplicates (organize first, then deduplicate)
python file_organizer.py D:\RecoveredFiles --remove-duplicates
```

Output example:
```
Recursively scanning folders...
Found 150 files, starting analysis...
Analysis complete, 150 files total

Processing January 2023 - 50 files...
  Processed 1000/1500 files...

Complete! Successfully organized 150 files

==================================================
Organization complete, starting duplicate detection and removal...
==================================================

Scanning organized files and calculating hashes...
Found 150 files, starting hash calculation...
Scanned 150 files

Found 5 groups of duplicate files, 8 duplicates total

Keep: 20230115001.jpg (2023-01-15 10:30:25)
  Delete: 20230115002.jpg (2023-01-15 10:35:10) - 2.45 MB
  Delete: 20230115003.jpg (2023-01-15 11:20:00) - 2.45 MB

Complete! Deleted 8 duplicate files, saved 18.50 MB
```

### Example 5: Complete Workflow

```bash
# Complete organization and deduplication in one go (with brand recognition and multi-threading)
python file_organizer.py H:\picture\JPEG --remove-duplicates --include-brand --threads 8 -o D:\OrganizedPhotos
```

### Example 6: Automatic Sequence Adjustment

When files already exist at the target location, the program automatically adjusts sequence numbers:

```
Processing January 2023 - 5 files...
  IMG_001.jpg -> 2023/01/20230115001.jpg
  IMG_002.jpg -> 2023/01/20230115002.jpg
  Sequence conflict, auto-adjusted: IMG_003.jpg -> 2023/01/20230115004.jpg (sequence 3 -> 4)
  IMG_004.jpg -> 2023/01/20230115005.jpg

Complete! Successfully organized 4 files
1 file had sequence number adjusted due to conflict
```

This feature ensures:
- All files are successfully organized, none are skipped
- New files automatically continue from existing file sequences when running multiple times
- No existing files are overwritten

### Example 7: Include Camera Brand Information

```bash
python file_organizer.py H:\picture\JPEG --include-brand
```

Output example:
```
Processing May 2023 - 10 files...
  DSC_0001.jpg -> 2023/05/Nikon_20230515001.jpg
    [Brand: Nikon]
  IMG_2345.jpg -> 2023/05/Canon_20230515002.jpg
    [Brand: Canon]
  PHOTO_001.jpg -> 2023/05/Sony_20230515003.jpg
    [Brand: Sony]
  random_pic.jpg -> 2023/05/20230515004.jpg

Complete! Successfully organized 10 files
```

### Example 8: Large File Processing (Batch Logging)

When processing large numbers of files, the program prints progress every 1000 files:

```bash
python file_organizer.py H:\picture\photos -o H:\picture\organized --threads 8
```

Output example:
```
Recursively scanning folders...
Found 5000 files, starting analysis...
  Analyzed 1000/5000 files...
  Analyzed 2000/5000 files...
  Analyzed 3000/5000 files...
  Analyzed 4000/5000 files...
Analysis complete, 5000 files total

Processing November 2024 - 2315 files...
  Processed 1000/2315 files...
  Processed 2000/2315 files...
  Sequence conflict, auto-adjusted: xxx.jpg -> 2024/11/20241124185.jpg (sequence 184 -> 185)

Complete! Successfully organized 5000 files

Processing 3 failed files...
Error log saved to: H:\picture\failed_files\error_log.txt
Failed files directory: H:\picture\failed_files
Moved 3 failed files to: H:\picture\failed_files
```

File naming format (with brand): `Brand_yyyymmdd00x.ext`
- Examples: `Canon_20230515001.jpg`, `Nikon_20231225003.jpg`
- If brand cannot be extracted, standard format is used: `20230515004.jpg`

## Error Handling

The program automatically handles various error situations:

- **Inaccessible paths**: Automatically skip and count
- **File move failures**: Log to error file
- **Hash calculation failures**: Skip deduplication check for that file
- **I/O device errors**: Skip problematic files, continue processing others

All failed files are logged to `failed_files/error_log.txt` for later investigation.

## Naming Rules

**Standard format**: `yyyymmdd00x.ext`

- `yyyy`: 4-digit year
- `mm`: 2-digit month
- `dd`: 2-digit day
- `00x`: 3-digit sequence number (001, 002, 003...)
- `.ext`: Original file extension

Examples:
- `20231225001.jpg` - 1st file on December 25, 2023
- `20231225002.jpg` - 2nd file on December 25, 2023
- `20240101001.pdf` - 1st file on January 1, 2024

**Format with brand** (using `--include-brand` parameter): `Brand_yyyymmdd00x.ext`

- Brand name placed at the beginning of filename
- Brand name extracted from image EXIF data (camera manufacturer)

Examples:
- `Canon_20231225001.jpg` - Photo taken with Canon camera
- `Nikon_20231225002.jpg` - Photo taken with Nikon camera
- `Sony_20231225003.jpg` - Photo taken with Sony camera
- `20231225004.jpg` - File with unrecognizable brand (uses standard format)

## Workflow Description

### Processing Order

The program uses an **organize-first, deduplicate-later** strategy to avoid deduplication impacting organization performance:

1. **Scan files**: Recursively scan all subfolders, skip inaccessible paths
2. **Analyze files**: Multi-threaded extraction of file information (date, brand, etc.)
3. **Organize files**: Organize by year/month and rename
4. **Handle failures**: Log errors, move failed files to dedicated directory
5. **Remove duplicates**: If `--remove-duplicates` is enabled, scan and remove duplicates after organization

### Duplicate File Detection

The program uses **MD5 hash algorithm** to compare file content:
- Files with identical content are identified as duplicates even if filenames differ
- Not affected by filename or creation time, only compares actual content
- For duplicate file groups, keeps the file with **earliest modification time**
- Deduplication performed **on organized files**, doesn't impact organization performance
- **Compare only within same folder**: Only compares files in the same year/month folder, no cross-folder comparison

### Failed File Handling

When encountering unprocessable files:
1. Automatically skip the file, continue processing others
2. Log error information to `failed_files/error_log.txt`
3. Attempt to move failed files to `failed_files` directory
4. Display failed file statistics after processing completes

## Important Notes

1. ⚠️ **Recommended to use `--dry-run` preview mode first** to check effects
2. 🗑️ **Deleting duplicate files is irreversible**, preview and confirm first
3. 📦 Program moves files, not copies - ensure you have backups
4. 🗂️ **Automatically processes all subfolders recursively**, including multi-level nested folders
5. 🔢 If target location has files with same name, program auto-increments sequence to ensure all files are processed
6. 💾 Ensure sufficient disk space
7. 🔐 Duplicate detection based on file content, large files may take longer
8. ⚡ Multi-threading accelerates processing but increases CPU and memory usage
9. 🛡️ Inaccessible files or folders are automatically skipped and processing continues
10. 📝 Failed files are logged and moved to `failed_files` directory
11. 🔄 Deduplication performed after file organization, doesn't impact organization performance

## System Requirements

- Python 3.6 or higher
- Basic functionality requires no additional packages (uses Python standard library only)
- **Optional dependency**: Pillow library (for extracting brand information from image EXIF data)
  ```bash
  pip install Pillow
  ```

## Performance Optimization Tips

**Recommendations for processing large numbers of files:**

1. **Use multi-threading**: Adjust thread count based on CPU cores (recommend 8-16 threads)
   ```bash
   python file_organizer.py <source_folder> --threads 8
   ```

2. **Batch processing**: If file count exceeds 100,000, recommend processing in batches

3. **Organize first, deduplicate later**: Program automatically optimized for this, no manual operation needed

4. **Check failed files**: After processing, check `failed_files/error_log.txt` to understand failure reasons

5. **Disk performance**: Using SSD can significantly improve processing speed

## FAQ

**Q: Are files copied or moved?**  
A: Files are moved (cut), not copied.

**Q: What happens if target folder already has files with same name?**  
A: Program automatically increments sequence number. For example, if 20231225001.jpg exists, it will use 20231225002.jpg, and so on, ensuring all files are organized.

**Q: Can it process files in subfolders?**  
A: Yes. Program automatically scans all subfolders recursively (including multi-level nesting) and processes all found files.

**Q: How to undo operations?**  
A: Program doesn't provide undo functionality. Recommend using `--dry-run` preview first, or backup important files before operation.

**Q: How to determine if files are duplicates?**  
A: Program calculates MD5 hash of files. Files with identical content are identified as duplicates, regardless of filename.

**Q: Which file is kept when deleting duplicates?**  
A: The file with earliest modification time is kept, newer copies are deleted. This preserves the original file.

**Q: What's the order of deduplication and organization?**  
A: Program **organizes files first**, then **removes duplicates** after organization completes. This avoids deduplication impacting organization performance, especially noticeable when processing large numbers of files.

**Q: Why organize first then deduplicate?**  
A: Because calculating file hashes (deduplication) is time-consuming. Organizing files first allows most files to be quickly organized, then deduplication is performed on organized files, improving overall efficiency.

**Q: Does deduplication compare across folders?**  
A: No. Deduplication only compares within **the same year/month folder**, no cross-folder comparison. For example, files from March 2021 are only compared with other files from the same month, not with files from April 2021 or other months. This is more reasonable and efficient.

**Q: What happens if program is run multiple times?**  
A: Program intelligently recognizes existing files and automatically adjusts sequence numbers, won't overwrite or lose any files.

**Q: Which image formats support brand recognition?**  
A: Supports common image formats: JPG, JPEG, PNG, TIFF, HEIC, HEIF, etc. Brand information is extracted from image EXIF data.

**Q: What if image has no EXIF data or brand can't be recognized?**  
A: Program uses standard naming format (without brand name), won't affect file organization process.

**Q: Can brand names be customized?**  
A: Current version automatically extracts from EXIF data, typically camera manufacturer name (e.g., Canon, Nikon, Sony, etc.).

**Q: Is subfolder structure preserved?**  
A: No. Program extracts all files from subfolders and reorganizes them by date into year/month folder structure. Original folder structure is not preserved.

**Q: Will processing be slow if there are many subfolders?**  
A: Program supports multi-threading, which can significantly improve speed. Use `--threads 8` parameter to accelerate processing. Program displays progress every 1000 files.

**Q: What to do when encountering inaccessible folders?**  
A: Program automatically skips inaccessible files or folders (e.g., I/O errors, permission issues), displays skipped path list at start, then continues processing other files.

**Q: How to improve processing speed?**  
A: Use `--threads` parameter to increase thread count. Recommend setting based on CPU cores, typically 8-16 threads. Note that too many threads may cause performance degradation.

**Q: Why is log output reduced?**  
A: To avoid excessive logs, program prints progress only every 1000 files. Only special cases like sequence conflicts are printed individually.

**Q: How are failed files handled?**  
A: Failed files are logged to `failed_files/error_log.txt` and attempted to be moved to `failed_files` directory. This allows separate viewing and handling of these files.

**Q: What to do when encountering many inaccessible files?**  
A: Program automatically skips these files and displays skip count. These files are usually caused by overly long paths, special characters, or I/O device errors. Program continues processing other accessible files.

**Q: Why does deduplication only occur within the same folder?**  
A: Because files from different time periods (year/month) typically shouldn't be compared. The same photo appearing in different months is reasonable (e.g., backup or organization). Only duplicate files within the same month need deletion. This avoids accidental deletion while significantly improving deduplication efficiency.
