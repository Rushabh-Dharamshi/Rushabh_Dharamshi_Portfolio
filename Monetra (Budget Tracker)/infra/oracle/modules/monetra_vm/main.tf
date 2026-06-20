data "oci_identity_availability_domains" "available" {
  compartment_id = var.tenancy_ocid
}

data "oci_core_images" "selected" {
  compartment_id           = var.tenancy_ocid
  operating_system         = var.image_operating_system
  operating_system_version = var.image_operating_system_version
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

locals {
  name_prefix         = "monetra-${var.environment}"
  availability_domain = var.availability_domain_name != "" ? var.availability_domain_name : data.oci_identity_availability_domains.available.availability_domains[var.availability_domain_index].name
  source_image_ocid   = var.image_ocid != "" ? var.image_ocid : data.oci_core_images.selected.images[0].id
  common_tags = {
    app         = "monetra"
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "oci_core_vcn" "monetra" {
  compartment_id = var.compartment_ocid
  cidr_block     = var.vcn_cidr
  display_name   = "${local.name_prefix}-vcn"
  dns_label      = "monetra${substr(var.environment, 0, 3)}"
  freeform_tags  = local.common_tags
}

resource "oci_core_internet_gateway" "monetra" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.monetra.id
  display_name   = "${local.name_prefix}-internet-gateway"
  enabled        = true
  freeform_tags  = local.common_tags
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.monetra.id
  display_name   = "${local.name_prefix}-public-route-table"
  freeform_tags  = local.common_tags

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.monetra.id
  }
}

resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.monetra.id
  display_name   = "${local.name_prefix}-public-security-list"
  freeform_tags  = local.common_tags

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    description = "SSH"
    protocol    = "6"
    source      = var.ssh_allowed_cidr

    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    description = "HTTP"
    protocol    = "6"
    source      = var.http_allowed_cidr

    tcp_options {
      min = 80
      max = 80
    }
  }

  ingress_security_rules {
    description = "HTTPS"
    protocol    = "6"
    source      = var.http_allowed_cidr

    tcp_options {
      min = 443
      max = 443
    }
  }

  dynamic "ingress_security_rules" {
    for_each = var.expose_app_debug_ports ? [3000, 8000] : []

    content {
      description = "Temporary Monetra debug port ${ingress_security_rules.value}"
      protocol    = "6"
      source      = var.http_allowed_cidr

      tcp_options {
        min = ingress_security_rules.value
        max = ingress_security_rules.value
      }
    }
  }
}

resource "oci_core_subnet" "public" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.monetra.id
  cidr_block                 = var.subnet_cidr
  display_name               = "${local.name_prefix}-public-subnet"
  dns_label                  = "public"
  prohibit_public_ip_on_vnic = false
  route_table_id             = oci_core_route_table.public.id
  security_list_ids          = [oci_core_security_list.public.id]
  freeform_tags              = local.common_tags
}

resource "oci_core_instance" "monetra" {
  availability_domain = local.availability_domain
  compartment_id      = var.compartment_ocid
  display_name        = var.instance_name
  shape               = var.instance_shape
  freeform_tags       = local.common_tags

  shape_config {
    ocpus         = var.ocpus
    memory_in_gbs = var.memory_in_gbs
  }

  create_vnic_details {
    assign_public_ip = true
    display_name     = "${local.name_prefix}-vnic"
    hostname_label   = "monetra-${substr(var.environment, 0, 3)}"
    subnet_id        = oci_core_subnet.public.id
  }

  source_details {
    source_type = "image"
    source_id   = local.source_image_ocid
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data = base64encode(templatefile("${path.module}/cloud-init.yaml.tftpl", {
      app_dir                = var.app_dir
      app_user               = "opc"
      expose_app_debug_ports = var.expose_app_debug_ports
      install_ollama         = var.install_ollama
      ollama_models          = var.ollama_models
    }))
  }
}
