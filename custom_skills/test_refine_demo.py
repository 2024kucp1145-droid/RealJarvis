
def execute(context=None):
    try:
            return {"success": True, "message": "Initial version output", "data": 1}

        # Refined based on request: add extra logging and return data=2
    except Exception as e:
        return {'success': False, 'message': f'Task failed with error: {e}', 'data': None}