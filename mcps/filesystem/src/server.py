"""
Filesystem MCP Server using FastMCP
Provides safe file operations
"""

from fastmcp import FastMCP
import os
import json
import logging
from pathlib import Path
# Import tool schemas (handle both relative and direct imports)
try:
    from .tool_schema import get_tool_schemas, get_resource_schemas
except ImportError:
    from tool_schema import get_tool_schemas, get_resource_schemas

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Reduce FastMCP logging noise during startup
logging.getLogger('fastmcp').setLevel(logging.WARNING)
logging.getLogger('mcp').setLevel(logging.WARNING)

# Create FastMCP server
mcp = FastMCP("Filesystem Operations 📁")

# Security: only allow operations in safe directories
ALLOWED_DIRS = ["/tmp", "/home/fschulz/dev/nelli-ai-scientist"]

def _check_path_security(path: str) -> bool:
    """Check if path is in allowed directories"""
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(allowed) for allowed in ALLOWED_DIRS)

@mcp.tool
async def read_file(path: str) -> dict:
    """Read the contents of a file
    
    Args:
        path: Path to the file to read
    """
    try:
        if not _check_path_security(path):
            return {"error": f"Access denied. Path must be in: {ALLOWED_DIRS}"}
        
        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}
        
        if not os.path.isfile(path):
            return {"error": f"Path is not a file: {path}"}
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "content": content,
            "path": path,
            "size": len(content.encode('utf-8')),
            "success": True
        }
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}

@mcp.tool
async def write_file(path: str, content: str) -> dict:
    """Write content to a file
    
    Args:
        path: Path to the file to write
        content: Content to write to the file
    """
    try:
        if not _check_path_security(path):
            return {"error": f"Access denied. Path must be in: {ALLOWED_DIRS}"}
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "path": path,
            "bytes_written": len(content.encode('utf-8')),
            "success": True
        }
    except Exception as e:
        return {"error": f"Failed to write file: {str(e)}"}

@mcp.tool
async def list_directory(path: str = "/tmp") -> dict:
    """List contents of a directory
    
    Args:
        path: Path to the directory to list
    """
    try:
        if not _check_path_security(path):
            return {"error": f"Access denied. Path must be in: {ALLOWED_DIRS}"}
        
        if not os.path.exists(path):
            return {"error": f"Directory not found: {path}"}
        
        if not os.path.isdir(path):
            return {"error": f"Path is not a directory: {path}"}
        
        entries = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            stat = os.stat(item_path)
            
            entries.append({
                "name": item,
                "type": "directory" if os.path.isdir(item_path) else "file",
                "size": stat.st_size if os.path.isfile(item_path) else None,
                "modified": stat.st_mtime
            })
        
        # Sort by name
        entries.sort(key=lambda x: x["name"])
        
        return {
            "entries": entries,
            "path": path,
            "count": len(entries),
            "success": True
        }
    except Exception as e:
        return {"error": f"Failed to list directory: {str(e)}"}

@mcp.tool
async def create_directory(path: str) -> dict:
    """Create a directory
    
    Args:
        path: Path to the directory to create
    """
    try:
        if not _check_path_security(path):
            return {"error": f"Access denied. Path must be in: {ALLOWED_DIRS}"}
        
        os.makedirs(path, exist_ok=True)
        
        return {
            "path": path,
            "success": True
        }
    except Exception as e:
        return {"error": f"Failed to create directory: {str(e)}"}

@mcp.tool
async def delete_file(path: str) -> dict:
    """Delete a file
    
    Args:
        path: Path to the file to delete
    """
    try:
        if not _check_path_security(path):
            return {"error": f"Access denied. Path must be in: {ALLOWED_DIRS}"}
        
        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}
        
        if not os.path.isfile(path):
            return {"error": f"Path is not a file: {path}"}
        
        os.remove(path)
        
        return {
            "path": path,
            "success": True
        }
    except Exception as e:
        return {"error": f"Failed to delete file: {str(e)}"}

@mcp.tool
async def file_exists(path: str) -> dict:
    """Check if a file or directory exists
    
    Args:
        path: Path to check
    """
    try:
        if not _check_path_security(path):
            return {"error": f"Access denied. Path must be in: {ALLOWED_DIRS}"}
        
        exists = os.path.exists(path)
        if exists:
            is_file = os.path.isfile(path)
            is_dir = os.path.isdir(path)
            stat = os.stat(path)
            
            return {
                "path": path,
                "exists": True,
                "type": "file" if is_file else "directory" if is_dir else "other",
                "size": stat.st_size if is_file else None,
                "modified": stat.st_mtime,
                "success": True
            }
        else:
            return {
                "path": path,
                "exists": False,
                "success": True
            }
    except Exception as e:
        return {"error": f"Failed to check file existence: {str(e)}"}

@mcp.tool
async def explore_directory_tree(path: str = None, max_depth: int = 3, include_files: bool = True) -> dict:
    """Explore directory structure recursively from current working directory or specified path
    
    Args:
        path: Starting directory path (defaults to current working directory)
        max_depth: Maximum depth to traverse (default: 3)
        include_files: Whether to include files in the output (default: True)
    """
    try:
        # Use current working directory if no path specified
        if path is None:
            path = os.getcwd()
        
        if not _check_path_security(path):
            return {"error": f"Access denied. Path must be in: {ALLOWED_DIRS}"}
        
        if not os.path.exists(path):
            return {"error": f"Directory not found: {path}"}
        
        if not os.path.isdir(path):
            return {"error": f"Path is not a directory: {path}"}
        
        def _explore_recursive(current_path: str, current_depth: int = 0) -> dict:
            """Recursively explore directory structure"""
            if current_depth > max_depth:
                return {"truncated": True, "reason": "max_depth_reached"}
            
            try:
                entries = []
                items = os.listdir(current_path)
                
                # Sort items: directories first, then files
                dirs = []
                files = []
                
                for item in items:
                    item_path = os.path.join(current_path, item)
                    try:
                        if os.path.isdir(item_path):
                            dirs.append(item)
                        elif include_files:
                            files.append(item)
                    except (PermissionError, OSError):
                        # Skip items we can't access
                        continue
                
                # Process directories
                for item in sorted(dirs):
                    item_path = os.path.join(current_path, item)
                    try:
                        stat = os.stat(item_path)
                        dir_entry = {
                            "name": item,
                            "type": "directory",
                            "path": item_path,
                            "modified": stat.st_mtime,
                        }
                        
                        # Recursively explore subdirectory
                        if current_depth < max_depth:
                            subdir_content = _explore_recursive(item_path, current_depth + 1)
                            if subdir_content:
                                dir_entry["contents"] = subdir_content
                        
                        entries.append(dir_entry)
                    except (PermissionError, OSError):
                        # Skip directories we can't access
                        continue
                
                # Process files
                if include_files:
                    for item in sorted(files):
                        item_path = os.path.join(current_path, item)
                        try:
                            stat = os.stat(item_path)
                            entries.append({
                                "name": item,
                                "type": "file",
                                "path": item_path,
                                "size": stat.st_size,
                                "modified": stat.st_mtime,
                            })
                        except (PermissionError, OSError):
                            # Skip files we can't access
                            continue
                
                return {
                    "entries": entries,
                    "entry_count": len(entries),
                    "depth": current_depth
                }
                
            except Exception as e:
                return {"error": f"Failed to explore {current_path}: {str(e)}"}
        
        # Start exploration
        result = _explore_recursive(path)
        
        return {
            "root_path": path,
            "max_depth": max_depth,
            "include_files": include_files,
            "tree": result,
            "success": True
        }
        
    except Exception as e:
        return {"error": f"Failed to explore directory tree: {str(e)}"}

# Add some example resources
@mcp.resource("filesystem://allowed-dirs")
def get_allowed_directories():
    """Get list of allowed directories for file operations"""
    return {
        "allowed_directories": ALLOWED_DIRS,
        "note": "File operations are restricted to these directories for security"
    }

@mcp.resource("filesystem://examples")
def get_examples():
    """Get example file operations"""
    return {
        "examples": [
            {"operation": "read_file", "path": "/tmp/test.txt"},
            {"operation": "write_file", "path": "/tmp/output.txt", "content": "Hello World"},
            {"operation": "list_directory", "path": "/tmp"}
        ]
    }

if __name__ == "__main__":
    # Run with stdio transport by default
    mcp.run()