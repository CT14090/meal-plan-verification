"""
Encryption Module - Handles encryption/decryption of sensitive student data
Uses Fernet symmetric encryption (AES-128 in CBC mode)
"""

import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self):
        """Initialize encryption with key from environment"""
        encryption_key = os.getenv('ENCRYPTION_KEY')
        
        if not encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY not found in environment variables. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        try:
            self.cipher = Fernet(encryption_key.encode())
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string
        
        Args:
            plaintext: String to encrypt (e.g., student name)
        
        Returns:
            Encrypted string (base64 encoded)
        """
        if not plaintext:
            return ""
        
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            raise Exception(f"Encryption failed: {e}")
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt encrypted string
        
        Args:
            encrypted_text: Encrypted string to decrypt
        
        Returns:
            Original plaintext string
        """
        if not encrypted_text:
            return ""
        
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_text.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            raise Exception(f"Decryption failed: {e}")
    
    def encrypt_dict(self, data: dict, fields: list) -> dict:
        """
        Encrypt specific fields in a dictionary
        
        Args:
            data: Dictionary containing data
            fields: List of field names to encrypt
        
        Returns:
            Dictionary with encrypted fields
        """
        encrypted_data = data.copy()
        for field in fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt(encrypted_data[field])
        return encrypted_data
    
    def decrypt_dict(self, data: dict, fields: list) -> dict:
        """
        Decrypt specific fields in a dictionary
        
        Args:
            data: Dictionary containing encrypted data
            fields: List of field names to decrypt
        
        Returns:
            Dictionary with decrypted fields
        """
        decrypted_data = data.copy()
        for field in fields:
            if field in decrypted_data and decrypted_data[field]:
                decrypted_data[field] = self.decrypt(decrypted_data[field])
        return decrypted_data


# Singleton instance
_encryption_manager = None

def get_encryption_manager() -> EncryptionManager:
    """Get or create encryption manager singleton"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def generate_new_key() -> str:
    """
    Generate a new encryption key
    
    Returns:
        New Fernet encryption key as string
    
    Usage:
        python -c "from config.encryption import generate_new_key; print(generate_new_key())"
    """
    return Fernet.generate_key().decode()


if __name__ == "__main__":
    # Test encryption
    print("Testing encryption module...")
    
    # Generate test key
    test_key = generate_new_key()
    print(f"\nGenerated test key: {test_key}")
    
    # Create temporary encryption manager
    os.environ['ENCRYPTION_KEY'] = test_key
    em = EncryptionManager()
    
    # Test string encryption
    test_name = "John Smith"
    encrypted = em.encrypt(test_name)
    decrypted = em.decrypt(encrypted)
    
    print(f"\nOriginal: {test_name}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    print(f"Match: {test_name == decrypted}")
    
    # Test dict encryption
    test_data = {
        'student_id': '12345',
        'student_name': 'Jane Doe',
        'card_rfid_uid': '04A3B2C145',
        'meal_plan_type': 'Premium'
    }
    
    encrypted_data = em.encrypt_dict(test_data, ['student_name', 'card_rfid_uid'])
    decrypted_data = em.decrypt_dict(encrypted_data, ['student_name', 'card_rfid_uid'])
    
    print("\n--- Dict Encryption Test ---")
    print(f"Original: {test_data}")
    print(f"Encrypted: {encrypted_data}")
    print(f"Decrypted: {decrypted_data}")
    print(f"Match: {test_data == decrypted_data}")