# Enforce best practices in Powershell
Set-StrictMode -Version 1.0
# Exit if a cmdlet fails
$ErrorActionPreference = "Stop"

# Configuration
$domain = "demo.local"
$plaintextPassword = "vagrant"

##################################################################################
# Password policy configuration
##################################################################################

Write-Host -fore green $ 'Running password policy logic'

# Ensure passwords never expire
net accounts /maxpwage:unlimited

# Disable automatic machine account password changes
Set-ItemProperty -Path 'Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\NetLogon\Parameters' -Name DisablePasswordChange -Value 1

# Allow weak passwords
secedit /export /cfg c:\secpol.cfg
(Get-Content C:\secpol.cfg).replace("PasswordComplexity = 1", "PasswordComplexity = 0") | Out-File C:\secpol.cfg
secedit /configure /db c:\windows\security\local.sdb /cfg c:\secpol.cfg /areas SECURITYPOLICY
rm -force c:\secpol.cfg -confirm:$false

##################################################################################
# Disable Antivirus
##################################################################################

if (Get-Module -ListAvailable -Name Defender) {
    Set-MpPreference -DisableRealtimeMonitoring $true
    New-ItemProperty -Path "Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows Defender" -Name DisableAntiSpyware -Value 1 -PropertyType DWORD -Force
}

#####################################################################################
# Forest installation
#####################################################################################

Write-Host -fore green $ 'Running forest installation'

$safeModeAdministratorPassword = ConvertTo-SecureString $plaintextPassword -AsPlainText -Force

# Set local Administrator account password to stop the error:
#   "The new domain cannot be created DC01: because the local Administrator account password does not meet requirements."
Write-Host -fore green $ 'Setting local administrator password'
Set-LocalUser `
    -Name Administrator `
    -AccountNeverExpires `
    -Password $safeModeAdministratorPassword `
    -PasswordNeverExpires:$true `
    -UserMayChangePassword:$true

Install-WindowsFeature AD-Domain-Services,RSAT-AD-AdminCenter,RSAT-ADDS-Tools -IncludeManagementTools -Verbose

#
# Install the Active Directory Domain Services (AD DS) environment
#

# Win32_operatingSystem ProductType
#   Work Station (1)
#   Domain Controller (2)
#   Server (3)
# https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-operatingsystem
$isDomainController = (Get-WmiObject -Class Win32_operatingSystem).ProductType -Eq 2
Write-Host -fore green $ 'IsDomainController='$isDomainController
if (!$isDomainController) {
    Write-Host -fore green $ 'Installing ADDS'
    $netbios = $domain.split('.')[0].ToUpperInvariant()
    Install-ADDSForest `
        -CreateDnsDelegation:$false `
        -DatabasePath "C:\Windows\NTDS" `
        -DomainMode "Win2012R2" `
        -DomainName $domain `
        -DomainNetbiosName $netbios `
        -ForestMode "Win2012R2" `
        -InstallDns:$true `
        -LogPath "C:\Windows\NTDS" `
        -NoRebootOnCompletion:$false `
        -SysvolPath "C:\Windows\SYSVOL" `
        -Force:$true `
        -SafeModeAdministratorPassword $safeModeAdministratorPassword `
        -Verbose
}

Write-Host -fore green $ 'Finished forest installation'
