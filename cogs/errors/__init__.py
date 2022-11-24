from .error_handler import ErrorHandler

def setup(client):
    client.add_cog(ErrorHandler(client))