from .reminders import Reminders

def setup(client):
    client.add_cog(Reminders(client))