# Raspberry Pi Car Dev Log #01 — Remote Connection

**Date:** 2026-10-07  
**Project:** Raspberry Pi 4 Robot Car

## Goal

The first step of this project was to establish a remote connection between my Windows PC and the Raspberry Pi.

This allows me to develop and control the robot car from my laptop without connecting a keyboard, mouse, and monitor to the Raspberry Pi.

## Step 1 — Find the Raspberry Pi

My Windows PC and Raspberry Pi were connected to the same network. I tested the connection using:

```powershell
ping raspberrypi.local
```

The Raspberry Pi was successfully discovered through its hostname, `raspberrypi.local`. The initial ping resolved to an IPv6 address and returned all four packets successfully with **0% packet loss**.

To request IPv4 explicitly, I also tried:

```powershell
ping -4 raspberrypi.local
```

## Step 2 — Connect via SSH

After confirming that the Raspberry Pi was reachable, I connected to it remotely using SSH:

```powershell
ssh <username>@raspberrypi.local
```

After authentication, I successfully entered the Raspberry Pi terminal from my Windows PC.

The connection architecture is now:

```text
Windows PC
    |
    | Wi-Fi / Local Network
    |
    v
Raspberry Pi 4
    |
    +-- SSH Remote Access [x]
    |
    +-- Robot Car Hardware
```

## What I Learned

- How devices discover each other on a local network
- The purpose of `raspberrypi.local`
- Basic differences between IPv4 and IPv6
- How to test network connectivity using `ping`
- How to remotely access a Raspberry Pi using SSH

## Current Progress

- [x] Raspberry Pi powered and connected to the network
- [x] Windows PC can discover the Raspberry Pi
- [x] `ping raspberrypi.local` works
- [x] SSH connection established
- [ ] Configure the Python development environment
- [ ] Launch Jupyter Notebook
- [ ] Test GPIO
- [ ] Control motors
- [ ] Add a camera
- [ ] Implement computer vision
- [ ] Build an autonomous robot car

## Next Step

The next goal is to configure the Python environment and launch **Jupyter Notebook** on the Raspberry Pi, so Python programs can be developed and tested remotely from the Windows browser.