import urllib.request
import struct
import io

def get_remote_file_size(url):
    req = urllib.request.Request(url, method='HEAD')
    with urllib.request.urlopen(req) as resp:
        return int(resp.headers.get('Content-Length'))

def fetch_range(url, start, end):
    req = urllib.request.Request(url)
    req.add_header('Range', f'bytes={start}-{end}')
    with urllib.request.urlopen(req) as resp:
        return resp.read()

def main():
    url = "https://uc.hackerearth.com/he-public-ap-south-1/CCTV%20Footage-20260529T160731Z-3-00144614ea.zip"
    print(f"Fetching remote size for {url}...")
    try:
        size = get_remote_file_size(url)
        print(f"File size: {size} bytes ({size / (1024*1024):.2f} MB)")
    except Exception as e:
        print(f"Error fetching size: {e}")
        return

    # ZIP central directory is at the end of the file.
    # Let's download the last 65 KB.
    tail_size = min(size, 65536)
    print(f"Downloading last {tail_size} bytes...")
    try:
        tail_data = fetch_range(url, size - tail_size, size - 1)
    except Exception as e:
        print(f"Error fetching range: {e}")
        return

    # Let's search for the End of Central Directory record (EOCD signature: 0x06054b50)
    eocd_sig = b'\x50\x4b\x05\x06'
    eocd_pos = tail_data.rfind(eocd_sig)
    if eocd_pos == -1:
        print("EOCD signature not found in tail.")
        return

    print(f"Found EOCD at offset {size - tail_size + eocd_pos}")
    eocd = tail_data[eocd_pos:]
    
    if len(eocd) < 22:
        print("EOCD too short.")
        return
        
    # Unpack EOCD (excluding the 4-byte signature):
    # 4 H (2 bytes each = 8 bytes) + 2 I (4 bytes each = 8 bytes) = 16 bytes from index 4 to 20
    num_disk, disk_cd, num_cd_disk, num_cd, size_cd, offset_cd = struct.unpack('<HHHHII', eocd[4:20])
    print(f"Central Directory offset: {offset_cd}, size: {size_cd}, records: {num_cd}")

    # Now let's fetch the Central Directory!
    print(f"Downloading Central Directory ({size_cd} bytes)...")
    try:
        cd_data = fetch_range(url, offset_cd, offset_cd + size_cd - 1)
    except Exception as e:
        print(f"Error fetching Central Directory: {e}")
        return

    # Parse Central Directory to get filenames
    entry_sig = b'\x50\x4b\x01\x02'
    pos = 0
    files = []
    while pos < len(cd_data):
        if cd_data[pos:pos+4] != entry_sig:
            break
        if pos + 46 > len(cd_data):
            break
        fn_len, extra_len, comment_len = struct.unpack('<HHH', cd_data[pos+28:pos+34])
        filename = cd_data[pos+46:pos+46+fn_len].decode('utf-8', errors='ignore')
        files.append(filename)
        pos += 46 + fn_len + extra_len + comment_len

    print("\nFiles in ZIP:")
    for f in files:
        print(f" - {f}")

if __name__ == "__main__":
    main()
