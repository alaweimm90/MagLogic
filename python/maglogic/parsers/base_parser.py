"""
Base parser class for micromagnetic simulation data.

This module provides the abstract base class for all file parsers in MagLogic,
ensuring consistent interfaces and error handling across different file formats.

Author: Dr. Meshal Alawein
Email: meshal@berkeley.edu
License: MIT
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Union
import numpy as np
import logging

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    """
    Abstract base class for micromagnetic simulation file parsers.
    
    This class defines the common interface that all parsers must implement,
    providing consistent error handling and data structures across different
    file formats (OOMMF, MuMax3, etc.).
    
    Attributes:
        verbose: Whether to print verbose output during parsing
        supported_extensions: List of file extensions this parser supports
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize base parser.
        
        Args:
            verbose: Enable verbose output during parsing
        """
        self.verbose = verbose
        self.supported_extensions = []
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up logging configuration."""
        if self.verbose:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.WARNING)
    
    @abstractmethod
    def parse_file(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse a simulation data file.
        
        Args:
            filepath: Path to the file to parse
            
        Returns:
            Dictionary containing parsed data with standardized keys:
            - 'magnetization': Magnetization data (if applicable)
            - 'coordinates': Spatial coordinates
            - 'time_series': Time-dependent data (if applicable)
            - 'metadata': File and simulation metadata
            - 'header': Original file header information
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid
            RuntimeError: If parsing fails
        """
        pass
    
    def validate_file(self, filepath: Union[str, Path]) -> bool:
        """
        Validate that a file can be parsed by this parser.
        
        Args:
            filepath: Path to the file to validate
            
        Returns:
            True if file can be parsed, False otherwise
        """
        filepath = Path(filepath)
        
        # Check file exists
        if not filepath.exists():
            logger.error(f"File does not exist: {filepath}")
            return False
        
        # Check file extension
        if self.supported_extensions and filepath.suffix not in self.supported_extensions:
            logger.warning(f"File extension {filepath.suffix} not in supported list: {self.supported_extensions}")
            return False
        
        # Check file is readable
        try:
            with open(filepath, 'r') as f:
                f.read(1)
        except (IOError, UnicodeDecodeError):
            try:
                with open(filepath, 'rb') as f:
                    f.read(1)
            except IOError:
                logger.error(f"Cannot read file: {filepath}")
                return False
        
        return True
    
    def get_file_info(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """
        Get basic information about a file without fully parsing it.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Dictionary with file information:
            - 'size': File size in bytes
            - 'extension': File extension
            - 'exists': Whether file exists
            - 'readable': Whether file can be read
        """
        filepath = Path(filepath)
        
        info = {
            'filepath': str(filepath),
            'filename': filepath.name,
            'extension': filepath.suffix,
            'exists': filepath.exists(),
            'readable': False,
            'size': 0
        }
        
        if info['exists']:
            info['size'] = filepath.stat().st_size
            info['readable'] = self.validate_file(filepath)
        
        return info
    
    @staticmethod
    def standardize_coordinates(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Standardize coordinate arrays to consistent format.
        
        Args:
            x, y, z: Coordinate arrays
            
        Returns:
            Dictionary with standardized coordinate arrays
        """
        return {
            'x': np.asarray(x),
            'y': np.asarray(y), 
            'z': np.asarray(z)
        }
    
    @staticmethod
    def standardize_magnetization(mx: np.ndarray, my: np.ndarray, mz: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Standardize magnetization arrays to consistent format.
        
        Args:
            mx, my, mz: Magnetization component arrays
            
        Returns:
            Dictionary with standardized magnetization arrays and derived quantities
        """
        mx_arr = np.asarray(mx)
        my_arr = np.asarray(my)
        mz_arr = np.asarray(mz)
        
        # Calculate derived quantities
        magnitude = np.sqrt(mx_arr**2 + my_arr**2 + mz_arr**2)
        
        # Avoid division by zero
        magnitude_safe = np.where(magnitude > 1e-15, magnitude, 1.0)
        
        # Unit vectors (normalized magnetization)
        mx_norm = mx_arr / magnitude_safe
        my_norm = my_arr / magnitude_safe
        mz_norm = mz_arr / magnitude_safe
        
        # Angles
        theta = np.arccos(np.clip(mz_norm, -1, 1))  # Polar angle (0 to π)
        phi = np.arctan2(my_arr, mx_arr)           # Azimuthal angle (-π to π)
        
        return {
            'mx': mx_arr,
            'my': my_arr,
            'mz': mz_arr,
            'magnitude': magnitude,
            'mx_norm': mx_norm,
            'my_norm': my_norm,
            'mz_norm': mz_norm,
            'theta': theta,
            'phi': phi
        }
    
    @staticmethod
    def calculate_volume_average(data: np.ndarray, weights: Optional[np.ndarray] = None) -> float:
        """
        Calculate volume-averaged value of a 3D data array.
        
        Args:
            data: 3D data array
            weights: Optional weight array (e.g., cell volumes)
            
        Returns:
            Volume-averaged value
        """
        data_arr = np.asarray(data)
        
        if weights is not None:
            weights_arr = np.asarray(weights)
            return np.average(data_arr, weights=weights_arr)
        else:
            return np.mean(data_arr)
    
    def _log_info(self, message: str):
        """Log info message if verbose mode is enabled."""
        if self.verbose:
            logger.info(message)
    
    def _log_warning(self, message: str):
        """Log warning message."""
        logger.warning(message)
    
    def _log_error(self, message: str):
        """Log error message."""
        logger.error(message)

class ParseError(Exception):
    """Exception raised when file parsing fails."""
    pass

class UnsupportedFormatError(ParseError):
    """Exception raised when file format is not supported."""
    pass

class CorruptedFileError(ParseError):
    """Exception raised when file appears to be corrupted."""
    pass