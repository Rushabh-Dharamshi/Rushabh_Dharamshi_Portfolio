terraform {
  required_version = ">= 1.5.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 6.0"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

module "monetra_vm" {
  source = "../../modules/monetra_vm"

  tenancy_ocid              = var.tenancy_ocid
  compartment_ocid          = var.compartment_ocid
  environment               = "staging"
  instance_name             = var.instance_name
  availability_domain_index = var.availability_domain_index
  availability_domain_name  = var.availability_domain_name
  instance_shape            = var.instance_shape
  ocpus                     = var.ocpus
  memory_in_gbs             = var.memory_in_gbs
  image_ocid                = var.image_ocid
  ssh_public_key            = var.ssh_public_key
  ssh_allowed_cidr          = var.ssh_allowed_cidr
  http_allowed_cidr         = var.http_allowed_cidr
  expose_app_debug_ports    = var.expose_app_debug_ports
  app_dir                   = var.app_dir
  install_ollama            = var.install_ollama
  ollama_models             = var.ollama_models
}

