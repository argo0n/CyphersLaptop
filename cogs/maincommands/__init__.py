from .maincommands import MainCommands

def setup(client):
    client.add_cog(MainCommands(client))