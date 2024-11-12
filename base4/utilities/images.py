from PIL import Image


def create_thumbnail(input_image_path, output_image_path, size=(128, 128)):
    try:
        with Image.open(input_image_path) as img:
            img.thumbnail(size)
            img.save(output_image_path)

    except Exception as e:
        raise
