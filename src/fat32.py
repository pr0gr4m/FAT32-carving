import psutil
import sys
from struct import *

class FAT32:
    def __init__(self, drive):
        if not self.test_drive(drive):
            sys.exit(1)

        self.data = open("\\\\.\\" + drive[:2], "rb")
        self.parse_bootsector()
        self.parse_fsinfo()
        self.parse_fat()

    def __del__(self):
        try:
            self.data.close()
        except:
            return

    def test_drive(self, drive):
        partition = {}
        for part in psutil.disk_partitions():
            partition[part.mountpoint] = (part.fstype, part.device)
        if drive in partition:
            if partition[drive][0] == "FAT32":
                return True
            else:
                print("Drive is not FAT32")
                return False
        else:
            print("Couldn't find the drive")
            return False

    def parse_bootsector(self):
        self.data.seek(0)
        bootsector = self.data.read(0x200)
        magic = unpack_from('>H', bootsector, 0x1fe)[0]
        if not magic == 0x55aa:
            print("Magic number of boot sector is not 0x55AA")
            sys.exit(1)
        self.bytes_per_sector = unpack_from('<H', bootsector, 0x0b)[0]
        self.sector_per_cluster = unpack_from('<B', bootsector, 0x0d)[0]
        self.reserved_sector = unpack_from('<H', bootsector, 0x0e)[0]
        self.number_of_fat = unpack_from('<B', bootsector, 0x10)[0]
        self.media_type = unpack_from('<B', bootsector, 0x15)[0]
        self.fat_size = unpack_from('<L', bootsector, 0x24)[0]
        self.rootdir_cluster_offset = unpack_from('<L', bootsector, 0x2c)[0]
        self.fsinfo_sector_offset = unpack_from('<H', bootsector, 0x30)[0]
        self.volume_label = unpack_from('<10s', bootsector, 0x47)[0]
        self.fs_type = unpack_from('<8s', bootsector, 0x52)[0]
        self.fat_size_byte = self.sector_to_byte(self.fat_size)
        self.cluster_count = int(self.fat_size_byte / 4)
        self.data_cluster_count = self.cluster_count - 2

        print("\t---------- Boot Sector Information ----------")
        print("\tBytes per Sector : ", self.bytes_per_sector)
        print("\tSector per Cluster : ", self.sector_per_cluster)
        print("\tReserved Sector Count : ", self.reserved_sector)
        print("\tNumber of FAT Table : ", self.number_of_fat)
        print("\tMedia Type : ", hex(self.media_type))
        print("\tFAT Size : ", self.fat_size)
        print("\tRoot Directory Cluster Offset : ", self.rootdir_cluster_offset)
        print("\tFSInfo Sector Offset : ", self.fsinfo_sector_offset)
        print("\tVolume Label : ", self.volume_label)
        print("\tFileSystem Type : ", self.fs_type)
        print("\tCluster Count : ", self.cluster_count)

    def parse_fsinfo(self):
        self.data.seek(0x200)
        fsinfo = self.data.read(0x200)
        magic = unpack_from('<L', fsinfo, 0x00)[0]
        if not magic == 0x41615252:
            print("Magic number of fsinfo is not 0x41615252")
            return
        self.free_cluster_count = unpack_from('<L', fsinfo, 0x1e8)[0]
        self.next_free_cluster_location = unpack_from('<L', fsinfo, 0x1ec)[0]

        print("\t---------- FSInfo Information ----------")
        print("\tFree Cluster Count : ", self.free_cluster_count)
        print("\tNext Cluster Location : ", self.next_free_cluster_location)

    def parse_fat(self):
        self.data.seek(self.sector_to_byte(self.reserved_sector))
        fat_metadata = self.data.read(0x08)
        self.fat_data_cluster = self.data.read(self.fat_size_byte - 0x08)
        media_type = hex(unpack_from('<L', fat_metadata, 0x00)[0])
        partition_status = hex(unpack_from('<L', fat_metadata, 0x04)[0])

        print("\t---------- FAT Information ----------")
        print("\tMedia Type : ", media_type)
        print("\tPartition Status : ", partition_status)

    def sector_to_byte(self, sector):
        return self.bytes_per_sector * sector

    def cluster_to_sector(self, cluster):
        return self.sector_per_cluster * cluster

    def carving_all(self):
        self.carving_ex(1)

    def carving_unallocated(self):
        self.carving_ex(self.next_free_cluster_location)

    def carving_ex(self, start_offset):
        cluster_num = start_offset
        unalloc_cluster_offset = self.sector_to_byte(
            self.reserved_sector +
            self.fat_size * 2 +
            self.cluster_to_sector(cluster_num)
        )
        while cluster_num <= self.free_cluster_count:
            self.data.seek(unalloc_cluster_offset)
            sig = self.match_signature(self.data.read(0x10), unalloc_cluster_offset)
            if sig:
                print(cluster_num + 1, "-", sig)    # start from cluster number 1
            cluster_num += 1
            unalloc_cluster_offset += self.sector_per_cluster * self.bytes_per_sector

    def match_signature(self, sig_data, offset):
        byte = unpack_from(">H", sig_data, 0x00)[0]
        if byte == 0x4d5a:      # MZ
            return "exe/dll"
        elif byte == 0x424d:
            return "bmp"
        elif byte == 0xffd8:
            return "jpg"
        else:
            byte = unpack_from(">L", sig_data, 0x00)[0]
            if byte == 0x504b0304:      # zip
                return self.match_signatrue_zip(offset)
            elif byte == 0x25504446:
                return "pdf"
            elif byte == 0x47494638:
                return "gif"
            elif byte == 0x89504e47:
                return "png"
            elif byte == 0x52494646:
                return "avi"

    def match_signatrue_zip(self, offset):
        self.data.seek(offset)
        zip_data = self.data.read(0x1000)
        zip_str = str(zip_data)
        if "word/" in zip_str:
            return "zip[docx]"
        elif "ppt/" in zip_str:
            return "zip[pptx]"
        elif "xl/" in zip_str:
            return "zip[xlsx]"
        else:
            name_len = unpack_from('<H', zip_data, 0x1a)[0]
            return "zip{" + zip_data[0x1e:0x1e+name_len].decode('euc-kr') + "}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        fat = FAT32(sys.argv[1] + ":\\")
        print("\n\t========== Carving Start ==========\n")
        if len(sys.argv) > 2 and sys.argv[2] == "all":
            fat.carving_all()
        else:
            fat.carving_unallocated()
        print("\n\t========== Carving Complete ==========")
    else:
        print("Usage: python3 " + sys.argv[0] + " <drive> [all]")