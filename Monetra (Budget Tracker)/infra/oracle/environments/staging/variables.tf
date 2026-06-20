variable "tenancy_ocid" {
  type      = string
  sensitive = true
}

variable "user_ocid" {
  type      = string
  sensitive = true
}

variable "fingerprint" {
  type      = string
  sensitive = true
}

variable "private_key_path" {
  type      = string
  sensitive = true
}

variable "region" {
  type    = string
  default = "uk-london-1"
}

variable "compartment_ocid" {
  type      = string
  sensitive = true
}

variable "instance_name" {
  type    = string
  default = "monetra-staging-a1"
}

variable "availability_domain_index" {
  type    = number
  default = 0
}

variable "availability_domain_name" {
  type    = string
  default = ""
}

variable "instance_shape" {
  type    = string
  default = "VM.Standard.A1.Flex"
}

variable "ocpus" {
  type    = number
  default = 2
}

variable "memory_in_gbs" {
  type    = number
  default = 12
}

variable "image_ocid" {
  type    = string
  default = ""
}

variable "ssh_public_key" {
  type      = string
  sensitive = true
}

variable "ssh_allowed_cidr" {
  type    = string
  default = "0.0.0.0/0"
}

variable "http_allowed_cidr" {
  type    = string
  default = "0.0.0.0/0"
}

variable "expose_app_debug_ports" {
  type    = bool
  default = true
}

variable "app_dir" {
  type    = string
  default = "/opt/monetra"
}

variable "install_ollama" {
  type    = bool
  default = true
}

variable "ollama_models" {
  type    = list(string)
  default = ["qwen2.5:7b", "nomic-embed-text"]
}

