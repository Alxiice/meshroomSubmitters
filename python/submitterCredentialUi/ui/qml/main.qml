import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Window {
    id: root
    width: 400
    height: 250
    visible: true
    title: "Password Dialog"
    modality: Qt.ApplicationModal
    flags: Qt.Dialog
    
    // Signal to notify when dialog is accepted/rejected
    signal accepted()
    signal rejected()
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15
        
        Label {
            text: "Please enter your credentials"
            font.pointSize: 12
            font.bold: true
        }
        
        GridLayout {
            columns: 2
            rowSpacing: 10
            columnSpacing: 10
            Layout.fillWidth: true
            
            Label {
                text: "Username:"
            }
            
            TextField {
                id: usernameField
                Layout.fillWidth: true
                placeholderText: "Enter username"
                focus: true
                selectByMouse: true
                
                Keys.onReturnPressed: passwordField.forceActiveFocus()
            }
            
            Label {
                text: "Password:"
            }
            
            TextField {
                id: passwordField
                Layout.fillWidth: true
                placeholderText: "Enter password"
                echoMode: TextInput.Password
                selectByMouse: true
                
                Keys.onReturnPressed: acceptButton.clicked()
            }
        }
        
        CheckBox {
            id: showPasswordCheck
            text: "Show password"
            onCheckedChanged: {
                passwordField.echoMode = checked ? TextInput.Normal : TextInput.Password
            }
        }
        
        Item {
            Layout.fillHeight: true
        }
        
        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: 10
            
            Button {
                text: "Cancel"
                onClicked: {
                    root.rejected()
                    root.close()
                }
            }
            
            Button {
                id: acceptButton
                text: "OK"
                enabled: usernameField.text.length > 0 && passwordField.text.length > 0
                highlighted: true
                
                onClicked: {
                    backend.setCredentials(usernameField.text, passwordField.text)
                    root.accepted()
                    root.close()
                }
            }
        }
    }
}
