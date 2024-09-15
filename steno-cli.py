import argparse
import os
import numpy as np
from PIL import Image
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import threading

def transcribe(data, system="pitman"):
    if system == "pitman":
        return ''.join([chr((ord(c) + 100) % 256) for c in data])
    elif system == "gregg":
        return ''.join([chr((ord(c) + 150) % 256) for c in data])
    raise ValueError(f"Unsupported system: {system}")

def encrypt_message(message, key):
    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(message.encode(), AES.block_size))
    return cipher.iv + ct_bytes

def decrypt_message(ciphertext, key):
    iv = ciphertext[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext[AES.block_size:]), AES.block_size)
    return plaintext.decode()

def encode_image(image_path, message, output_path=None, key=None):
    img = Image.open(image_path).convert('RGB')
    img_array = np.array(img)
    
    if key:
        message = encrypt_message(message, key)
    
    bits = ''.join(format(byte, '08b') for byte in message) + '00000000'
    flat_img = img_array.flatten()

    if len(bits) > len(flat_img):
        raise ValueError("Message too large for image capacity.")

    for i in range(len(bits)):
        flat_img[i] = (flat_img[i] & ~1) | int(bits[i])

    img_array = flat_img.reshape(img_array.shape)
    encoded_img = Image.fromarray(img_array)
    
    if not output_path:
        output_path = f"encoded_{os.path.basename(image_path)}"
    
    encoded_img.save(output_path)

def decode_image(image_path, key=None):
    img = Image.open(image_path).convert('RGB')
    img_array = np.array(img).flatten()

    bits = [str(pixel & 1) for pixel in img_array]
    bytes_list = [''.join(bits[i:i+8]) for i in range(0, len(bits), 8)]
    message = bytes([int(byte, 2) for byte in bytes_list])
    message = message.split(b'\x00', 1)[0]

    if key:
        message = decrypt_message(message, key)

    return message.decode()

def handle_files(files, action, system="pitman", message=None, key=None, threads=1):
    def process_file(f):
        if action == "decode":
            decoded_data = decode_image(f, key)
            print(transcribe(decoded_data, system=system))
        elif action == "encode":
            if not message:
                raise ValueError("Message required for encoding.")
            encode_image(f, message, key=key)

    if threads > 1:
        thread_list = []
        for f in files:
            t = threading.Thread(target=process_file, args=(f,))
            thread_list.append(t)
            t.start()
        for t in thread_list:
            t.join()
    else:
        for f in files:
            process_file(f)

def main():
    parser = argparse.ArgumentParser(prog="steno-cli", description="High-performance steganography tool")
    parser.add_argument("files", nargs="+", help="Image files (.jpg, .jpeg, .png)")
    parser.add_argument("-a", "--action", choices=["encode", "decode"], required=True, help="encode/decode action")
    parser.add_argument("-s", "--system", default="pitman", help="Transcription system (default: pitman)")
    parser.add_argument("-m", "--message", help="Message to encode (for encoding only)")
    parser.add_argument("-k", "--key", help="Encryption key (16, 24, or 32 bytes) for message encryption")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Number of threads for parallel processing")
    
    args = parser.parse_args()
    
    key = None
    if args.key:
        if len(args.key) not in [16, 24, 32]:
            raise ValueError("Key must be 16, 24, or 32 bytes long.")
        key = args.key.encode()

    handle_files(args.files, args.action, args.system, args.message, key, args.threads)

if __name__ == "__main__":
    main()
