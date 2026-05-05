```
amixer -c 0 sset 'LINEOUT' on
amixer -c 0 sset 'Left LINEOUT Mux' 'LOMixer'
amixer -c 0 sset 'Right LINEOUT Mux' 'ROMixer'
amixer -c 0 sset 'Left Output Mixer DACL' on
amixer -c 0 sset 'Right Output Mixer DACR' on

amixer -c 0 sset 'digital volume' 0
amixer -c 0 sset 'LINEOUT volume' 20
```

```
sudo alsactl store
```

```
systemctl status alsa-restore.service
sudo systemctl enable --now alsa-restore.service
```
