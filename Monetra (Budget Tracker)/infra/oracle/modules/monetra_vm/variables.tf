variable "tenancy_ocid" {
  description = "Oracle Cloud tenancy OCID. Used for availability domain and image lookup."
  type        = string
}

variable "compartment_ocid" {
  description = "Oracle Cloud compartment OCID where resources will be created."
  type        = string
}

variable "environment" {
  description = "Environment name, for example staging or production."
  type        = string
}

variable "instance_name" {
  description = "Display name for the Monetra VM."
  type        = string
}

variable "availability_domain_index" {
  description = "Zero-based availability domain index. Change this if Oracle reports out of host capacity."
  type        = number
  default     = 0
}

variable "availability_domain_name" {
  description = "Optional exact availability domain name. Leave empty to use availability_domain_index."
  type        = string
  default     = ""
}

variable "instance_shape" {
  description = "Oracle compute shape. A1 Flex is the preferred Always Free ARM option."
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "ocpus" {
  description = "OCPU count for flexible shapes."
  type        = number
  default     = 2
}

variable "memory_in_gbs" {
  description = "RAM for flexible shapes."
  type        = number
  default     = 12
}

variable "image_ocid" {
  description = "Optional custom image OCID. Leave empty to auto-select the newest compatible image."
  type        = string
  default     = ""
}

variable "image_operating_system" {
  description = "Operating system name used when auto-selecting an image."
  type        = string
  default     = "Oracle Linux"
}

variable "image_operating_system_version" {
  description = "Operating system version used when auto-selecting an image."
  type        = string
  default     = "9"
}

variable "vcn_cidr" {
  description = "CIDR range for the Monetra VCN."
  type        = string
  default     = "10.40.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR range for the public subnet."
  type        = string
  default     = "10.40.1.0/24"
}

variable "ssh_allowed_cidr" {
  description = "CIDR allowed to SSH into the VM. Use your own IP/32 for stricter production access."
  type        = string
  default     = "0.0.0.0/0"
}

variable "http_allowed_cidr" {
  description = "CIDR allowed to access HTTP/HTTPS."
  type        = string
  default     = "0.0.0.0/0"
}

variable "expose_app_debug_ports" {
  description = "Expose ports 3000 and 8000 directly. Useful for early staging only; prefer 80/443 later."
  type        = bool
  default     = true
}

variable "ssh_public_key" {
  description = "Public SSH key allowed to connect as opc."
  type        = string
  sensitive   = true
}

variable "app_dir" {
  description = "Directory created on the VM for Monetra deployments."
  type        = string
  default     = "/opt/monetra"
}

variable "install_ollama" {
  description = "Whether cloud-init should install Ollama on first boot."
  type        = bool
  default     = true
}

variable "ollama_models" {
  description = "Ollama models to pull during first boot. Keep this small on free-tier VMs."
  type        = list(string)
  default     = ["qwen2.5:7b", "nomic-embed-text"]
}

