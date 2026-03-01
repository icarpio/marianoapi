# aquarium/utils.py — versión corregida
# El cambio clave: format='png' y flags='preserve_transparency'
# para que Cloudinary NO convierta a JPEG y respete el canal alfa.

import base64
import uuid
import cloudinary
import cloudinary.uploader


def upload_fish_image(image_base64: str, user_id: int) -> dict:
    """
    Sube la imagen del pez a Cloudinary conservando transparencia.

    Args:
        image_base64: string data-URL completo, p.ej. "data:image/png;base64,iVBOR..."
                      o solo la parte base64 sin prefijo.
        user_id:      ID del usuario dueño del pez.

    Returns:
        dict con { 'url': str, 'public_id': str }
    """
    # Eliminar el prefijo data-URL si viene incluido
    if ',' in image_base64:
        image_base64 = image_base64.split(',', 1)[1]

    image_data = base64.b64decode(image_base64)

    public_id = f'aquarium/fish_{user_id}_{uuid.uuid4().hex}'

    result = cloudinary.uploader.upload(
        image_data,
        public_id        = public_id,
        overwrite        = True,
        resource_type    = 'image',

        # ─── CLAVE: mantener PNG con transparencia ───────────────────
        format           = 'png',          # fuerza salida PNG (no JPEG)
        # ────────────────────────────────────────────────────────────
    )

    return {
        'url':       result['secure_url'],
        'public_id': result['public_id'],
    }


def delete_fish_image(public_id: str) -> None:
    """Elimina una imagen de Cloudinary por su public_id."""
    cloudinary.uploader.destroy(public_id, resource_type='image')