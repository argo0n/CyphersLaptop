from .dev import Developer

def setup(client):
    client.add_cog(Developer(client))