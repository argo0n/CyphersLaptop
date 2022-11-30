from .others import Others

def setup(client):
    client.add_cog(Others(client))