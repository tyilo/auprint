# auprint

Allows you to setup Aarhus University's printers on their `prt11.uni.au.dk` server.

For other possible ways of printing on Aarhus University's printers see https://matfystutor.dk/wiki/Printere (danish)

Requires CUPS, smbclient and python3 to work.

Additionally your user must have permissions to add printers using `lpadmin`.

Adding printer admin permissions to an user
==
If you do not have permission to add a printer using `lpadmin`, you probably just need to add your user to a specific group.

On Arch Linux this should work:

```
sudo gpasswd sys -a "$(id -un)"
```

On Ubuntu this should work:

```
sudo gpasswd lpadmin -a "$(id -un)"
```

After adding yourself to the group, you will need to logout and login again to make the changes take effect.


TODO
==

- Use pycups instead of using cups CLI for doing stuff
