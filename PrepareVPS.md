# Preparing VPS for Dank Vibes Bot

1. `sudo su` if you are not root.
2. `apt install `
##PostgreSQL installation
We will be installing it from the official repository.

2. `sudo apt-get install wget ca-certificates`
3. `wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -`
4. `sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'`

Now we will actually install PostgreSQL into the server.
5. `sudo apt-get update`
6. `sudo apt-get upgrade`
7. `sudo apt-get install mlocate firewalld chromium-chromedriver postgresql postgresql-contrib`
        
    - `mlocate` is used to locate files in the system.
    - `chromium-chromedriver` is used for the screenshot command.

8. `pg_lsclusters` to see where the log is located. 
9. Locate these two files using `mlocate`:
   1. `pg_hba.conf`
   2. `postgresql.conf`
   
10. Enter `postgresql.conf` using `nano`.
    1. Change the listening port to `5433`.
    2. Change the `listen_addresses = '*'`

11. Enter `pg_hba` using `nano`. 
    1. Add a line under `#IPv4 local connections` that allow for outside users to connect. It is recommended you specify another user, not the `postgres` user.
    
       1. `host    all             dankvibes       0.0.0.0/0               scram-sha-256`
    2. Remove the line `host    all             all             127.0.0.1/32            scram-sha-256`, since we already allowed connection through peer.
    3. Reject all incoming connections aiming for the user `postgres` from outside, by adding the line
       1. `host    all             postgres        0.0.0.0/0               reject`
       2. 
12. `service postgresql restart`
13. `sudo systemctl start postgresql.service`
    1. Make sure it's running smoothly by checking `service postgresql status` and `pg_lsclusters` (especially checking the port).
14. To go to PostgreSQL shell, use `sudo -u postgres psql`
15. `createuser --interactive` to create a new user.
    1. Change the password with 
    ```
    ALTER USER dankvibes PASSWORD 'myPassword';
    ```
## Configuring the firewall

15. We'll use firewalld (or firewall-cmd) for it.
16. `sudo systemctl enable firewalld`
17. Make sure it's running using `sudo firewall-cmd --state`
18. ```
    sudo firewall-cmd --permanent --add-port=5000/tcp
    sudo firewall-cmd --permanent --add-port=5433/tcp
    sudo firewall-cmd --permanent --add-port=22/tcp
    sudo firewall-cmd --reload
    ```
19. From then on, use the PostgreSQL shell or pgAdmin to configure, backup and restore.


   
 