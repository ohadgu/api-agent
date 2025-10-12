import platform
import logging
# from typing import Dict, Any
# from app.celery_app import celery
from ..infra.models import TaskRun


logger = logging.getLogger(__name__)


# class RegistryActionError(Exception):
#     pass


def registry_action(action: str, key: str, value_name: str, value_data: str = None):
    try:
        import winreg
        if action == "GET":
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as reg_key:
                    value_data, _ = winreg.QueryValueEx(reg_key, value_name)
                    return {"success": True, "value_data": value_data}
            except Exception as e:
                return {"success": False, "error": f"Value '{value_name}' not found in key '{key}': {e}"}

        elif action == "SET":
            if value_data is None or value_data == "":
                # raise RegistryActionError("Value data must be provided and not be empty for SET action.")
                raise ValueError("Value data must be provided and not be empty for SET action.")
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as reg_key:
                winreg.SetValueEx(reg_key, value_name, 0, winreg.REG_SZ, value_data)
                return {"success": True, "message": f"Successfully set {value_name} to {value_data} in {key}"}

        else:  # action == "DELETE":
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as reg_key:
                winreg.DeleteValue(reg_key, value_name)
                return {"success": True, "message": f"Successfully deleted {value_name} from {key}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# def enqueue_registry_action(action: str, key: str, value_name: str, value_data: str, db) -> dict:
    """
    Enqueue registry action task and create database record.

    Args:
        action: Registry action (GET/SET/DELETE)
        key: Registry key path
        value_name: Registry value name
        value_data: Registry value data (for SET operations)
        db: Database session

    Returns:
        dict: Task information including task_id and status
    """
    

    # # Prepare task arguments
    # task_args = [action, key]
    # task_kwargs = {}

    # if value_name is not None:
    #     task_kwargs['value_name'] = value_name
    # if value_data is not None:
    #     task_kwargs['value_data'] = value_data

    # Queue the task
    result = registry_action.apply_async(action, key, value_name, value_data, db)

    # # Create database record
    # tr = TaskRun(
    #     id=result.id,
    #     name=registry_action.name,
    #     status="PENDING",
    #     args_json=task_args,
    #     kwargs_json=task_kwargs
    # )
    # db.add(tr)
    # db.commit()

    return {
        "task_id": result.id,
        "status": "queued",
        "name": registry_action.name,
        "action": action,
        "key": key
    }




# def _execute_registry_operation(action: str, key: str, value_name: str, value_data: str) -> dict:
#     """
#     Execute Windows registry operation with cross-platform handling.

#     Args:
#         action: Registry action (GET/SET/DELETE)
#         key: Registry key path
#         value_name: Registry value name
#         value_data: Registry value data (for SET operations)

#     Returns:
#         dict: Operation result with success/failure status

#     Raises:
#         ValueError: If operation fails or is not supported
#     """
#     # Check if running on Windows
#     if platform.system() != "Windows":
#         raise ValueError(f"Registry operations are only supported on Windows systems. Current OS: {platform.system()}")

#     try:
#         # Parse the registry hive from the key
#         hive_map = {
#             "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
#             "HKLM": winreg.HKEY_LOCAL_MACHINE,
#             "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
#             "HKCU": winreg.HKEY_CURRENT_USER,
#             "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
#             "HKCR": winreg.HKEY_CLASSES_ROOT,
#             "HKEY_USERS": winreg.HKEY_USERS,
#             "HKU": winreg.HKEY_USERS,
#             "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG,
#             "HKCC": winreg.HKEY_CURRENT_CONFIG,
#         }

#         # Split the key into hive and subkey
#         key_parts = key.split("\\", 1)
#         if len(key_parts) < 2:
#             raise ValueError(f"Invalid registry key format: {key}. Expected format: 'HIVE\\Subkey'")

#         hive_name = key_parts[0]
#         subkey = key_parts[1]

#         if hive_name not in hive_map:
#             raise ValueError(f"Unsupported registry hive: {hive_name}")

#         hive = hive_map[hive_name]

#         if action == "GET":
#             if not value_name:
#                 raise ValueError("value_name is required for GET operations")

#             with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as reg_key:
#                 value, reg_type = winreg.QueryValueEx(reg_key, value_name)
#                 return {
#                     "action": "GET",
#                     "key": key,
#                     "value_name": value_name,
#                     "value_data": str(value),
#                     "reg_type": reg_type,
#                     "status": "SUCCESS"
#                 }

#         elif action == "SET":
#             if not value_name or value_data is None:
#                 raise ValueError("value_name and value_data are required for SET operations")

#             try:
#                 # Try to open existing key
#                 with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as reg_key:
#                     winreg.SetValueEx(reg_key, value_name, 0, winreg.REG_SZ, value_data)
#             except FileNotFoundError:
#                 # Create the key if it doesn't exist
#                 with winreg.CreateKey(hive, subkey) as reg_key:
#                     winreg.SetValueEx(reg_key, value_name, 0, winreg.REG_SZ, value_data)

#             return {
#                 "action": "SET",
#                 "key": key,
#                 "value_name": value_name,
#                 "value_data": value_data,
#                 "status": "SUCCESS"
#             }

#         elif action == "DELETE":
#             if not value_name:
#                 raise ValueError("value_name is required for DELETE operations")

#             with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as reg_key:
#                 winreg.DeleteValue(reg_key, value_name)

#             return {
#                 "action": "DELETE",
#                 "key": key,
#                 "value_name": value_name,
#                 "status": "SUCCESS"
#             }

#         else:
#             raise ValueError(f"Unsupported action: {action}")

#     except ImportError:
#         raise ValueError("winreg module not available - registry operations require Windows")
#     except FileNotFoundError as e:
#         raise ValueError(f"Registry key or value not found: {e}")
#     except PermissionError as e:
#         raise ValueError(f"Permission denied accessing registry: {e}")
#     except Exception as e:
#         logger.error(f"Registry operation failed: {e}")
#         raise ValueError(f"Registry operation failed: {e}")


# # @celery.task(name="system.registry_action", max_retries=2)
# def registry_action(action: str, key: str, value_name: str = None, value_data: str = None):
#     """
#     Perform Windows registry operations.

#     Parameters:
#         action (str): Registry action - GET, SET, or DELETE
#         key (str): Registry key path (e.g., 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Example')
#         value_name (str, optional): Registry value name
#         value_data (str, optional): Registry value data (required for SET)

#     Returns:
#         dict: Operation result with status and details

#     Raises:
#         ValueError: If operation fails or parameters are invalid
#     """
#     if not action or action not in ["GET", "SET", "DELETE"]:
#         raise ValueError("action must be one of: GET, SET, DELETE")

#     if not key or not key.strip():
#         raise ValueError("key cannot be empty")

#     try:
#         result = _execute_registry_operation(
#             action=action.upper(),
#             key=key.strip(),
#             value_name=value_name.strip() if value_name else None,
#             value_data=value_data if value_data is not None else None
#         )

#         logger.info(f"Registry {action} operation successful for key: {key}")
#         return result

#     except ValueError:
#         # Re-raise ValueError with original message
#         raise
#     except Exception as e:
#         logger.error(f"Unexpected error in registry_action: {e}")
#         raise ValueError(f"Registry operation failed: {e}")


# def enqueue_registry_action(action: str, key: str, value_name: str, value_data: str, db) -> dict:
#     """
#     Enqueue registry action task and create database record.

#     Args:
#         action: Registry action (GET/SET/DELETE)
#         key: Registry key path
#         value_name: Registry value name
#         value_data: Registry value data (for SET operations)
#         db: Database session

#     Returns:
#         dict: Task information including task_id and status
#     """
    

#     # Prepare task arguments
#     task_args = [action, key]
#     task_kwargs = {}

#     if value_name is not None:
#         task_kwargs['value_name'] = value_name
#     if value_data is not None:
#         task_kwargs['value_data'] = value_data

#     # Queue the task
#     res = registry_action.apply_async(args=task_args, kwargs=task_kwargs)

#     # Create database record
#     tr = TaskRun(
#         id=res.id,
#         name=registry_action.name,
#         status="PENDING",
#         args_json=task_args,
#         kwargs_json=task_kwargs
#     )
#     db.add(tr)
#     db.commit()

#     return {
#         "task_id": res.id,
#         "status": "queued",
#         "name": registry_action.name,
#         "action": action,
#         "key": key
#     }
