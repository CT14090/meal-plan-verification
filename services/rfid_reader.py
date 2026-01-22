"""
RFID Reader Service - Handles ACR122U NFC/RFID card reading
Reads MIFARE Classic 1K cards and extracts UID
"""

import threading
import time
from smartcard.System import readers
from smartcard.util import toHexString
from utils.logger import get_logger

logger = get_logger(__name__)

class RFIDReaderService:
    """
    Service for reading RFID cards using ACR122U reader
    Runs in background thread and calls callback when card is detected
    """
    
    def __init__(self, callback=None):
        """
        Initialize RFID reader service
        
        Args:
            callback: Function to call when card is detected
                     Signature: callback(card_uid: str)
        """
        self.callback = callback
        self.running = False
        self.thread = None
        self.reader = None
    
    def start(self):
        """Start the RFID reader service in background thread"""
        if self.running:
            logger.warning("RFID reader service already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        logger.info("RFID reader service started")
    
    def stop(self):
        """Stop the RFID reader service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("RFID reader service stopped")
    
    def _get_reader(self):
        """
        Get the first available card reader
        
        Returns:
            Reader object or None if no reader found
        """
        try:
            available_readers = readers()
            
            if not available_readers:
                logger.error("No card readers found. Is ACR122U connected?")
                return None
            
            # Use first available reader (typically ACR122U)
            reader = available_readers[0]
            logger.info(f"Using reader: {reader}")
            return reader
        except Exception as e:
            logger.error(f"Error getting card reader: {e}")
            return None
    
    def _read_loop(self):
        """
        Main loop that continuously polls for RFID cards
        Runs in background thread
        """
        logger.info("RFID read loop started")
        last_uid = None
        last_read_time = 0
        debounce_seconds = 2  # Ignore same card within 2 seconds
        
        while self.running:
            try:
                # Get reader if not already initialized
                if not self.reader:
                    self.reader = self._get_reader()
                    if not self.reader:
                        time.sleep(5)  # Wait before retrying
                        continue
                
                # Try to connect to a card
                connection = self.reader.createConnection()
                try:
                    connection.connect()
                    
                    # Card detected! Get UID
                    # Command: Get UID (APDU command for MIFARE)
                    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
                    data, sw1, sw2 = connection.transmit(GET_UID)
                    
                    # Check if command was successful (sw1=0x90, sw2=0x00)
                    if sw1 == 0x90 and sw2 == 0x00:
                        # Convert UID bytes to hex string
                        uid = toHexString(data).replace(" ", "").upper()
                        
                        # Debounce: ignore if same card read within debounce period
                        current_time = time.time()
                        if uid != last_uid or (current_time - last_read_time) > debounce_seconds:
                            logger.info(f"Card detected: {uid}")
                            
                            # Call callback function
                            if self.callback:
                                try:
                                    self.callback(uid)
                                except Exception as e:
                                    logger.error(f"Error in card callback: {e}")
                            
                            last_uid = uid
                            last_read_time = current_time
                    
                except Exception as e:
                    # No card present or read error (expected when no card)
                    pass
                finally:
                    try:
                        connection.disconnect()
                    except:
                        pass
                
                # Small delay between reads
                time.sleep(0.2)
            
            except Exception as e:
                logger.error(f"Error in RFID read loop: {e}")
                time.sleep(1)
        
        logger.info("RFID read loop stopped")
    
    def read_card_once(self, timeout=5):
        """
        Read a card once (blocking call)
        Useful for testing or manual card enrollment
        
        Args:
            timeout: Maximum seconds to wait for a card
        
        Returns:
            Card UID string or None if timeout
        """
        try:
            reader = self._get_reader()
            if not reader:
                return None
            
            logger.info(f"Waiting for card (timeout: {timeout}s)...")
            start_time = time.time()
            
            while (time.time() - start_time) < timeout:
                connection = reader.createConnection()
                try:
                    connection.connect()
                    
                    # Get UID
                    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
                    data, sw1, sw2 = connection.transmit(GET_UID)
                    
                    if sw1 == 0x90 and sw2 == 0x00:
                        uid = toHexString(data).replace(" ", "").upper()
                        logger.info(f"Card read: {uid}")
                        return uid
                
                except:
                    pass
                finally:
                    try:
                        connection.disconnect()
                    except:
                        pass
                
                time.sleep(0.2)
            
            logger.warning("Card read timeout")
            return None
        
        except Exception as e:
            logger.error(f"Error reading card: {e}")
            return None


def test_reader():
    """Test function to verify RFID reader is working"""
    print("=== RFID Reader Test ===")
    print("This will test the ACR122U reader connection.")
    print("Make sure the reader is connected via USB.\n")
    
    # Setup logging
    from utils.logger import setup_logging
    setup_logging()
    
    # Create reader service
    def on_card_detected(uid):
        print(f"\n✅ Card Detected!")
        print(f"   UID: {uid}")
        print(f"   Length: {len(uid)} characters")
        print(f"   This UID can be used in the database.\n")
    
    service = RFIDReaderService(callback=on_card_detected)
    
    print("Starting RFID reader service...")
    print("Wave a MIFARE card near the reader.\n")
    print("Press Ctrl+C to stop.\n")
    
    service.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
        service.stop()
        print("Test complete!")


if __name__ == "__main__":
    test_reader()