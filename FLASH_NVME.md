# Flashing Jetson Image to NVMe SSD

This guide provides step-by-step instructions for flashing a Jetson system image directly onto an NVMe SSD. This procedure is designed for use from a **Linux computer**.

## Prerequisites

- **Linux computer** (Ubuntu, Debian, or similar distribution)
- **256GB+ NVMe SSD** (or larger)
- **Latest release image** from the releases (see below)
- **Administrator access** (sudo privileges)

## Important Notes

- ⚠️ **This procedure will completely erase all data on the target NVMe SSD**
- ⚠️ **Double-check the device name before proceeding - selecting the wrong drive will result in data loss**
- 📦 The compressed image (`.img.zst`) is approximately **15GB**
- 💾 The decompressed image (`.img`) is approximately **50+GB**
- 🔍 **Always verify you're targeting the correct drive** before executing destructive commands

## Finding the Latest Release Image

**Download the latest release image from the [GitHub releases page](https://github.com/implyinfer/jetson-orin-nano-field-kit/releases).**

The releases page contains the most up-to-date system images. Always use the latest release image when flashing your NVMe SSD.

**Note:** The example URL below is for reference only and may not be the latest version:
```
https://r2.implyinfer.com/release-images/checkpoint_3.img.zst
```

**Always check the [releases page](https://github.com/implyinfer/jetson-orin-nano-field-kit/releases) for the latest release image.**

## Step-by-Step Instructions

### 1. Identify Your NVMe SSD Device

First, identify the device name of your NVMe SSD:

```bash
lsblk -o NAME,SIZE,MODEL
```

This will show output like:
```
NAME    SIZE  MODEL
sda     512G  Samsung SSD 980 PRO
sdb     1T    Some Other Drive
```

**Make absolutely sure you identify the correct device.** In this example, `/dev/sda` is the 512GB NVMe SSD we want to flash.

**Common device names:**
- `/dev/sda` - First SATA/NVMe device
- `/dev/nvme0n1` - First NVMe device (alternative naming, though sometimes this could be the main storage on the linux computer - don't use this since it'll erase your entire drive!)
- `/dev/sdb`, `/dev/sdc` - Additional storage devices

**If you're unsure, STOP and verify before proceeding.**

### 2. Unmount the NVMe SSD (if mounted)

If the NVMe SSD is currently mounted, unmount it:

```bash
# Check if mounted
mount | grep /dev/sda

# Unmount all partitions (replace sda with your device)
sudo umount /dev/sda*
```

### 3. Download and Decompress the Image

#### Download the Image

Download the latest release image (`.img.zst` file) from the releases:

```bash
# Example (replace with latest release URL)
wget https://r2.implyinfer.com/release-images/checkpoint_3.img.zst
```

#### Decompress the Image

The image is compressed using `zstd`. Decompress it:

```bash
# Install zstd if not already installed
sudo apt-get update
sudo apt-get install -y zstd

# Decompress the image
zstd -d checkpoint_3.img.zst -o jetson_min.img
```

**Note:** This will take several minutes as it decompresses ~15GB to ~50GB.

### 4. Wipe the SSD Clean

**This step prevents GPT corruption and ensures a clean flash:**

```bash
# Replace /dev/sda with your NVMe device name
sudo wipefs -a /dev/sda
sudo sgdisk --zap-all /dev/sda
sudo dd if=/dev/zero of=/dev/sda bs=1M count=20
sync
```

### 5. Flash the Image to NVMe SSD

Flash the decompressed image to your NVMe SSD:

```bash
# Replace /dev/sda with your NVMe device name
# Replace jetson_min.img with your actual image filename
sudo dd if=jetson_min.img of=/dev/sda bs=64M status=progress oflag=direct
sync
```

**This step will take 10-30 minutes depending on your system and SSD speed.**

The `status=progress` flag shows transfer progress, and `oflag=direct` ensures direct I/O for better performance.

### 6. Repair GPT (Mandatory)

After writing a reduced-size image, you must repair the GPT partition table:

```bash
sudo sgdisk -e /dev/sda
sudo partprobe /dev/sda
```

Verify the partitions are visible:

```bash
lsblk /dev/sda
```

You should see output like:
```
sda
├── sda1  ~50G  ext4
├── sda2
└── ...
└── sda15
```

### 7. Expand Partition 1 to Fill Entire SSD

The image was created for a smaller drive. Expand partition 1 to use the full 512GB capacity:

```bash
sudo parted /dev/sda
```

Inside the `parted` interactive shell:

```
(parted) print
(parted) resizepart 1 100%
(parted) quit
```

This updates the GPT partition entry so partition 1 spans the entire drive (instead of ~50GB).

### 8. Expand the Filesystem

Now expand the ext4 filesystem to fill the expanded partition:

```bash
# Run filesystem check first
sudo e2fsck -f /dev/sda1

# Resize the filesystem to fill the partition
sudo resize2fs /dev/sda1
```

**This step may take a few minutes** as it expands the filesystem.

### 9. Validate the Expansion

Verify that the filesystem now uses the full capacity:

```bash
df -h /dev/sda1
```

You should see output like:
```
Filesystem      Size  Used  Avail  Use%  Mounted on
/dev/sda1       470G   XG    YG     Z%   /mnt
```

The size should now be approximately **470GB** or near the full size of the nvme drive (accounting for filesystem overhead), indicating the expansion was successful.

### 10. Safely Remove and Install

Safely remove the NVMe SSD from your Linux computer:

```bash
# Ensure all writes are complete
sync

# If mounted, unmount
sudo umount /dev/sda1
```

Now you can safely remove the NVMe SSD and install it in your Jetson Orin Nano.

### 11. Boot the Jetson

Install the NVMe SSD in your Jetson Orin Nano and boot. The system should:

- ✅ Boot normally
- ✅ Use the flashed image
- ✅ Have a full usable root filesystem
- ✅ Require no further manual fixes

## Troubleshooting

### Device Not Found

If `lsblk` doesn't show your NVMe SSD:
- Ensure the SSD is properly connected
- Check USB-to-NVMe adapter compatibility (if using one)
- Try `sudo fdisk -l` to see all block devices

### Permission Denied

If you get permission errors:
- Ensure you're using `sudo` for all commands
- Check that no processes are using the device: `sudo lsof | grep /dev/sda`

### GPT Repair Fails

If `sgdisk -e` fails:
- Try: `sudo sgdisk --zap-all /dev/sda` again
- Then re-flash the image from step 5

### Filesystem Expansion Fails

If `resize2fs` fails:
- Ensure `e2fsck` completed successfully first
- Try: `sudo e2fsck -f -y /dev/sda1` to force repair
- Then retry `resize2fs`

### Boot Issues After Installation

If the Jetson doesn't boot:
- Verify the image was flashed correctly (re-check steps 5-6)
- Ensure the Jetson is configured to boot from NVMe
- Check Jetson boot configuration in recovery mode

## Summary

This procedure:
1. Identifies your NVMe SSD device
2. Downloads and decompresses the release image
3. Wipes the SSD clean
4. Flashes the ~50GB image to the SSD
5. Repairs the GPT partition table
6. Expands the partition to fill the 512GB drive
7. Expands the filesystem to use the full capacity
8. Validates the expansion

After completion, your Jetson Orin Nano will boot with a fully expanded filesystem using the entire NVMe SSD capacity with all the benefits of the Jetson Orin Nano Field Kit by imply+infer.

