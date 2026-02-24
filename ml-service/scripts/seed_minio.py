#!/usr/bin/env python3
"""Загружает тестовые изображения в MinIO для тестов."""

import sys
import os
from PIL import Image
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from modelforge.config import Settings
from modelforge.storage.s3_client import S3StorageService

settings = Settings()
storage = S3StorageService(settings)


def create_test_image(size=(512, 512), color: str = 'lightblue'):
    """Создает простое тестовое изображение с градиентом."""
    img = Image.new('RGB', size, color=color)

    # Добавляем простой градиент для реалистичности
    pixels = img.load()
    for i in range(size[0]):
        for j in range(size[1]):
            # Градиент по горизонтали: затемняем к правому краю
            factor = 1.0 - (i / size[0]) * 0.3
            r, g, b = img.getpixel((0, j))  # берем базовый цвет
            pixels[i, j] = (
                int(r * factor),
                int(g * factor),
                int(b * factor)
            )
    return img


def main():
    print("📤 Uploading test images to MinIO...")

    # Разные цвета для разных тестовых изображений
    colors = ['lightblue', 'lightcoral', 'lightgreen', 'plum', 'khaki']

    for i, color in enumerate(colors):
        img = create_test_image(color=color)
        key = f"test/photo_{i}.jpg"

        with io.BytesIO() as f:
            img.save(f, format='JPEG', quality=85)
            f.seek(0)
            s3_path = storage.upload_bytes(key, f.read())
            print(f"✅ Uploaded {s3_path}")

    print("🎉 Test images ready!")


if __name__ == "__main__":
    main()
